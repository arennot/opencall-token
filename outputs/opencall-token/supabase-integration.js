// OpenCall Token - Supabase 集成
// 在 app.js 之后加载，添加数据库读写能力

const SB_URL = "https://mbmzekzhgbngpvdibfea.supabase.co";
const SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1ibXpla3poZ2JuZ3B2ZGliZmVhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODI4Njk0NjQsImV4cCI6MjA5ODQ0NTQ2NH0.Dc9qCbiyqd0RIbwuwZhbXdCL7QA5-q14CmfiGiEvp1I";
let supabaseOpps = [];
let supabaseReady = false;

async function loadFromSupabase() {
  if (SB_URL.startsWith("https://YOUR_PROJECT")) return;
  try {
    var sb = window.supabase.createClient(SB_URL, SB_KEY);
    var r = await sb
      .from("opportunities")
      .select("*")
      .eq("status", "published")
      .order("posted_at", { ascending: false });
    if (!r.error && r.data && r.data.length > 0) {
      supabaseOpps = r.data.map(function(o) {
        if (o.is_local) o._local = true;
        return o;
      });
    }
    supabaseReady = true;
  } catch (e) {
    console.warn("Supabase unavailable, using fallback data");
  }
}

// 保存社区投稿到 Supabase
async function submitToSupabase(item) {
  if (SB_URL.startsWith("https://YOUR_PROJECT")) return;
  try {
    var sb = window.supabase.createClient(SB_URL, SB_KEY);
    await sb.from("opportunities").insert({
      title: item.title,
      type: item.type,
      organization: item.organization,
      deadline: item.deadline || null,
      location: item.location,
      disciplines: item.disciplines,
      funding: item.funding || null,
      description: item.description,
      url: item.url || null,
      source: "community",
      posted_at: item.posted_at,
      featured: false,
      is_local: true,
      status: "draft",
    }).execute();
  } catch (e) {
    console.warn("Failed to submit to Supabase:", e);
  }
}

// 重写 render 函数以包含 Supabase 数据
var _origRender = window.render || function(){};
window.render = function() {
  _origRender();
};

// 在页面加载后初始化
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initSupabase);
} else {
  initSupabase();
}

async function initSupabase() {
  await loadFromSupabase();
  if (supabaseOpps.length > 0) {
    // 将 Supabase 数据注入原有的 opportunities 数组
    // 重写 render 函数以包含 Supabase 和 localStorage 数据
    window.render = function() {
      var localOpps = [];
      try { localOpps = JSON.parse(localStorage.getItem("oct_localopps") || "[]"); } catch(e) {}
      localOpps = localOpps.map(function(o) { o._local = true; return o; });
      
      var items = supabaseOpps.concat(localOpps);
      
      // 应用筛选和排序（复用原有逻辑）
      var cv = window.currentView || "all";
      var cs = window.currentSearch || "";
      var cSort = window.currentSort || "newest";
      
      if (cv === "local") items = localOpps;
      else if (cv !== "all") items = items.filter(function(o) { return o.type === cv; });
      
      if (cs) {
        var q = cs.toLowerCase();
        items = items.filter(function(o) {
          return (o.title || "").toLowerCase().indexOf(q) !== -1 ||
                 (o.organization || "").toLowerCase().indexOf(q) !== -1 ||
                 (o.location || "").toLowerCase().indexOf(q) !== -1 ||
                 (o.description || "").toLowerCase().indexOf(q) !== -1;
        });
      }
      
      if (cSort === "deadline") {
        items.sort(function(a, b) { return (deadlineSortVal(a.deadline) || 9999999999999) - (deadlineSortVal(b.deadline) || 9999999999999); });
      } else if (cSort === "deadline-desc") {
        items.sort(function(a, b) { return (deadlineSortVal(b.deadline) || 9999999999999) - (deadlineSortVal(a.deadline) || 9999999999999); });
      } else {
        items.sort(function(a, b) { return new Date(b.posted_at || 0) - new Date(a.posted_at || 0); });
      }
      
      renderCards(items);
    };
  }
  window.render();
}

// 独立的卡片渲染函数
function renderCards(items) {
  document.getElementById("resultCount").textContent = "共 " + items.length + " 个机会";
  var grid = document.getElementById("cardsGrid");
  if (items.length === 0) {
    grid.innerHTML = '<div class="empty-state"><svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg><p>没有找到匹配的机会</p></div>';
    return;
  }
  grid.innerHTML = items.map(function(o) {
    var l = deadlineLabel(o.deadline);
    var bc = TYPE_CLASS[o.type] || "oc";
    var bl = TYPE_LABELS[o.type] || "公开征稿";
    if (o._local) { bc = "local"; bl = "社区提交"; }
    return '<div class="card" data-id="' + o.id + '"><div class="card-body"><span class="card-badge ' + bc + '">' + bl + '</span><h2 class="card-title">' + o.title + '</h2><div class="card-org">' + o.organization + '</div><div class="card-meta"><span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg><span class="' + l.cls + '">' + l.text + '</span></span><span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>' + (o.location || "") + '</span></div><div class="card-tags">' + (o.disciplines || []).map(function(d) { return '<span class="card-tag">' + d + '</span>'; }).join("") + '</div><p class="card-desc">' + (o.description || "") + '</p></div><div class="card-footer"><button class="card-btn view-details" data-id="' + o.id + '">查看详情</button></div></div>';
  }).join("");
  document.querySelectorAll(".view-details").forEach(function(btn) {
    btn.addEventListener("click", function(e) {
      e.stopPropagation();
      var id = btn.getAttribute("data-id");
      openModal(id);
    });
  });
  document.querySelectorAll(".card").forEach(function(card) {
    card.addEventListener("click", function() {
      var id = card.getAttribute("data-id");
      openModal(id);
    });
  });
}

// 拦截社区提交表单，额外写入 Supabase
document.addEventListener("DOMContentLoaded", function() {
  var origSubmit = document.getElementById("submitForm").onsubmit;
  document.getElementById("submitForm").addEventListener("submit", async function(e) {
    // 原有的提交处理已经在 app.js 中完成（写 localStorage）
    // 我们现在额外写一份到 Supabase
    var f = e.target;
    var item = {
      title: f.formTitle.value,
      type: f.formType.value,
      organization: f.formOrg.value,
      deadline: f.formDeadline.value || null,
      location: f.formLocation.value,
      disciplines: f.formDisciplines.value ? f.formDisciplines.value.split(",").map(function(s) { return s.trim(); }) : [],
      funding: f.formFunding.value || "",
      description: f.formDesc.value,
      url: f.formUrl.value,
      posted_at: new Date().toISOString().slice(0, 10),
    };
    await submitToSupabase(item);
  });
});

