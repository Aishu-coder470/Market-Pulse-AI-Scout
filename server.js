/**
 * Node.js Express API — serves scraper results to React dashboard
 * Run: node server.js
 */

const express = require("express");
const cors    = require("cors");
const fs      = require("fs");
const path    = require("path");

const app  = express();
const PORT = process.env.PORT || 3001;

app.use(cors());
app.use(express.json());

// ── Serve the dashboard HTML file ──
// This tells the server: when someone visits localhost:3001,
// send them the index.html file from the dashboard folder
app.use(express.static(path.join(__dirname, "..", "dashboard")));

// ── Helper: load latest analysis ──
function loadAnalysis() {
  const filePath = path.join(__dirname, "..", "scraper", "analysis_results.json");
  if (!fs.existsSync(filePath)) {
    // Return mock data if real scraper hasn't run yet
    return [
      {
        competitor: "Notion",
        url: "https://notion.so/pricing",
        change_score: 72,
        has_changes: true,
        current_prices: ["$10/mo", "$15/mo", "$18/mo"],
        current_plans: ["Free", "Plus", "Business", "Enterprise"],
        ai_summary: "Notion dropped their Plus plan price from $16 to $10/mo — a 37% reduction likely targeting Linear and Coda. Their Enterprise tier now includes SSO by default, removing a key upsell barrier.",
        changes: [
          { type: "price_removed", detail: "Price $16/mo disappeared from pricing page", severity: "high" },
          { type: "price_added",   detail: "New price $10/mo detected on Plus plan",      severity: "high" }
        ],
        checked_at: new Date().toISOString(),
        analyzed_at: new Date().toISOString()
      },
      {
        competitor: "Linear",
        url: "https://linear.app/pricing",
        change_score: 28,
        has_changes: true,
        current_prices: ["$8/mo", "$16/mo"],
        current_plans: ["Free", "Basic", "Business", "Enterprise"],
        ai_summary: "Linear added a new Basic plan at $8/user/month, positioned between Free and Business. This closes the gap with Jira pricing and signals a push into mid-market.",
        changes: [
          { type: "plan_added", detail: "New plan 'Basic' appeared in plan list", severity: "medium" }
        ],
        checked_at: new Date().toISOString(),
        analyzed_at: new Date().toISOString()
      },
      {
        competitor: "Vercel",
        url: "https://vercel.com/pricing",
        change_score: 0,
        has_changes: false,
        current_prices: ["$20/mo", "$400/mo"],
        current_plans: ["Hobby", "Pro", "Enterprise"],
        ai_summary: "No significant changes detected since last scan. Pricing and feature structure remain stable.",
        changes: [],
        checked_at: new Date().toISOString(),
        analyzed_at: new Date().toISOString()
      }
    ];
  }
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

// ── GET /api/competitors ──
app.get("/api/competitors", (req, res) => {
  try {
    const data = loadAnalysis();
    res.json({ success: true, data, count: data.length });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// ── GET /api/stats ──
app.get("/api/stats", (req, res) => {
  try {
    const data = loadAnalysis();
    const stats = {
      total_competitors: data.length,
      changes_detected:  data.filter(d => d.has_changes).length,
      high_severity:     data.filter(d => d.change_score >= 50).length,
      avg_change_score:  Math.round(data.reduce((s, d) => s + d.change_score, 0) / data.length),
      last_run:          data[0]?.analyzed_at || new Date().toISOString()
    };
    res.json({ success: true, data: stats });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// ── GET /api/health ──
app.get("/api/health", (req, res) => {
  res.json({ status: "ok", timestamp: new Date().toISOString() });
});

app.listen(PORT, () => {
  console.log(`\n🚀 CompeteIQ API running at http://localhost:${PORT}`);
  console.log(`📊 Open your dashboard at: http://localhost:${PORT}`);
  console.log(`\nAPI endpoints:`);
  console.log(`   GET  /api/competitors`);
  console.log(`   GET  /api/stats`);
  console.log(`   GET  /api/health`);
  console.log(`   GET  /api/health`);
});
