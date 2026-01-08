/**
 * Interface Inventory - Local Testing Server
 * 
 * Simple web UI for testing the extraction pipeline locally.
 * Upload 1-2 screenshots, provide app context, get JSON output.
 */

require('dotenv').config();
const express = require('express');
const multer = require('multer');
const { spawn } = require('child_process');
const path = require('path');

const app = express();
const upload = multer({ storage: multer.memoryStorage() });
const PORT = 3456;

app.use(express.json());
// Serve static files from dev/ directory (for index.html test UI)
app.use(express.static(path.join(__dirname, 'dev')));
// Also serve rendering_engine from root
app.use('/rendering_engine', express.static(path.join(__dirname, 'rendering_engine')));

/**
 * POST /extract
 * 
 * Body (multipart/form-data):
 * - images: 1-2 image files (order = state sequence)
 * - app_name: string (e.g., "mercury.com")
 * - app_description: string (paragraph describing the app)
 * 
 * Streams progress events as SSE if Accept: text/event-stream
 */
app.post('/extract', upload.array('images', 2), async (req, res) => {
  const useSSE = req.headers.accept === 'text/event-stream';
  
  if (useSSE) {
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    res.flushHeaders();
  }
  try {
    const { app_name, app_description } = req.body;
    const images = req.files;

    if (!images || images.length === 0) {
      return res.status(400).json({ error: 'At least one image required' });
    }

    console.log(`\n${'='.repeat(60)}`);
    console.log(`Processing ${images.length} image(s) for: ${app_name || 'Unknown App'}`);
    console.log(`${'='.repeat(60)}`);

    const results = [];

    for (let i = 0; i < images.length; i++) {
      const image = images[i];
      const imageBase64 = image.buffer.toString('base64');
      const filename = image.originalname || `screenshot_${i + 1}.png`;

      console.log(`\n[${i + 1}/${images.length}] Processing: ${filename}`);

      // Build input for Python pipeline
      const pipelineInput = {
        image_base64: imageBase64,
        filename: filename,
        app_name: app_name || null,
        app_description: app_description || null,
        sequence: i + 1,
        total_frames: images.length
      };

      // Progress callback for SSE
      const onProgress = useSSE ? (progress) => {
        res.write(`data: ${JSON.stringify(progress)}\n\n`);
      } : null;

      // Call Python pipeline
      const result = await runPipeline(pipelineInput, onProgress);
      results.push({
        sequence: i + 1,
        filename: filename,
        ...result
      });
    }

    // If multiple images, wrap in series structure
    const output = images.length === 1 
      ? results[0]
      : {
          app_context: {
            name: app_name || null,
            description: app_description || null
          },
          capture_mode: 'state_sequence',
          frame_count: images.length,
          frames: results
        };

    console.log(`\n✓ Complete`);
    
    if (useSSE) {
      // Send final result as SSE event
      res.write(`data: ${JSON.stringify({ type: 'complete', result: output })}\n\n`);
      res.end();
    } else {
      res.json(output);
    }

  } catch (error) {
    console.error('Error:', error);
    if (useSSE) {
      res.write(`data: ${JSON.stringify({ type: 'error', error: error.message })}\n\n`);
      res.end();
    } else {
      res.status(500).json({ error: error.message });
    }
  }
});

/**
 * Run Python extraction pipeline
 * @param {object} input - Pipeline input
 * @param {function} onProgress - Optional callback for progress events
 */
function runPipeline(input, onProgress = null) {
  return new Promise((resolve, reject) => {
    const pythonPath = process.env.PYTHON_PATH || path.join(__dirname, 'venv', 'bin', 'python3');
    const scriptPath = path.join(__dirname, 'extract.py');

    const proc = spawn(pythonPath, [scriptPath], {
      cwd: __dirname,
      env: { ...process.env }
    });

    let stdout = '';
    let stderr = '';

    proc.stdin.write(JSON.stringify(input));
    proc.stdin.end();

    proc.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    proc.stderr.on('data', (data) => {
      const chunk = data.toString();
      stderr += chunk;
      
      // Parse progress events from stderr
      const lines = chunk.split('\n');
      for (const line of lines) {
        if (line.startsWith('PROGRESS:')) {
          try {
            const progress = JSON.parse(line.slice(9));
            if (onProgress) onProgress(progress);
          } catch (e) {
            // Not valid JSON, skip
          }
        }
      }
      
      // Log to console
      process.stderr.write(data);
    });

    proc.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(`Pipeline exited with code ${code}: ${stderr}`));
        return;
      }

      try {
        const result = JSON.parse(stdout);
        resolve(result);
      } catch (e) {
        reject(new Error(`Failed to parse pipeline output: ${stdout}`));
      }
    });
  });
}

app.listen(PORT, () => {
  console.log(`\n${'='.repeat(60)}`);
  console.log(`Interface Inventory - Local Testing`);
  console.log(`${'='.repeat(60)}`);
  console.log(`\nOpen: http://localhost:${PORT}`);
  console.log(`\nEndpoint: POST /extract`);
  console.log(`  - images: 1-2 files (order = state sequence)`);
  console.log(`  - app_name: application domain/name`);
  console.log(`  - app_description: context paragraph`);
  console.log(`\n${'='.repeat(60)}\n`);
});
