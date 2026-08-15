#!/usr/bin/env node
const readline = require("readline");

const API_KEY = process.env.SUPERTHREAD_API_KEY || "stp-cda685a27a55057acc6f916117317a80.FXOR5T34yHvtD37MmdY5yTO95_q_1CASdFwZIN98gShMDE8lK8HaI7C8_8e6mfQm";
const ENDPOINT = "https://api.superthread.com/mcp/app";

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false
});

rl.on("line", async (line) => {
  line = line.trim();
  if (!line) return;

  try {
    const req = JSON.parse(line);

    // Notifications (no id) don't require an HTTP response
    if (req.method && req.method.startsWith("notifications/")) {
      return;
    }

    const response = await fetch(ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${API_KEY}`
      },
      body: line
    });

    if (response.ok) {
      const data = await response.text();
      if (data && data.trim()) {
        process.stdout.write(data.trim() + "\n");
      }
    } else {
      const errText = await response.text();
      const errRes = {
        jsonrpc: "2.0",
        id: req.id || null,
        error: {
          code: -32603,
          message: `Superthread API Error ${response.status}: ${errText}`
        }
      };
      process.stdout.write(JSON.stringify(errRes) + "\n");
    }
  } catch (err) {
    process.stderr.write(`Bridge error: ${err.message}\n`);
  }
});
