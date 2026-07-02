// OpenCall Token — Supabase 集成（数据层，渲染由 app.js 统一处理）

const SB_URL = "https://mbmzekzhgbngpvdibfea.supabase.co";
const SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1ibXpla3poZ2JuZ3B2ZGliZmVhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODI4Njk0NjQsImV4cCI6MjA5ODQ0NTQ2NH0.Dc9qCbiyqd0RIbwuwZhbXdCL7QA5-q14CmfiGiEvp1I";
let supabaseOpps = [];

async function loadFromSupabase() {
  if (SB_URL.startsWith("https://YOUR_PROJECT")) return;
  try {
    var sb = window.supabase.createClient(SB_URL, SB_KEY);
    var r = await sb.from("opportunities").select("*").eq("status", "published").order("posted_at", { ascending: false });
    if (!r.error && r.data && r.data.length > 0) {
      supabaseOpps = r.data.map(function (o) {
        if (o.is_local) o._local = true;
        return o;
      });
    }
  } catch (e) {
    console.warn("Supabase unavailable, using fallback data");
  }
}

async function submitToSupabase(item) {
  if (SB_URL.startsWith("https://YOUR_PROJECT")) return Promise.resolve();
  try {
    var sb = window.supabase.createClient(SB_URL, SB_KEY);
    await sb.from("opportunities").insert({
      title: item.title, type: item.type, organization: item.organization,
      deadline: item.deadline || null, location: item.location,
      disciplines: item.disciplines, funding: item.funding || null,
      description: item.description, url: item.url || null,
      source: "community", posted_at: item.posted_at,
      featured: false, is_local: true, status: "draft",
    });
  } catch (e) {
    console.warn("Failed to submit to Supabase:", e);
  }
}