// Netzwerktopologie & Mermaid-Visualisierung (#324)

var topologyScales = {};
var topologyPositions = {};

function initMermaidTopology() {
  if (typeof mermaid !== "undefined") {
    var isDark = document.documentElement.getAttribute("data-theme") === "dark";
    mermaid.initialize({
      startOnLoad: false,
      theme: isDark ? "dark" : "default",
      securityLevel: "loose",
      flowchart: {
        useMaxWidth: false,
        htmlLabels: true,
        curve: "basis"
      }
    });

    document.querySelectorAll(".mermaid:not([data-processed='true'])").forEach(function(el) {
      mermaid.run({ nodes: [el] }).then(function() {
        el.setAttribute("data-processed", "true");
        setupPanZoom(el.closest(".topology-viewport"));
      }).catch(function(err) {
        console.warn("Mermaid render warning:", err);
      });
    });
  }
}

function setupPanZoom(viewport) {
  if (!viewport || viewport.dataset.panInitialized) return;
  viewport.dataset.panInitialized = "true";

  var mermaidEl = viewport.querySelector(".mermaid");
  if (!mermaidEl) return;

  var id = viewport.id.replace("viewport-", "");
  topologyScales[id] = 1.0;
  topologyPositions[id] = { x: 0, y: 0 };

  var isDragging = false;
  var startX, startY;

  viewport.addEventListener("mousedown", function(e) {
    if (e.target.closest("button") || e.target.closest("a")) return;
    isDragging = true;
    startX = e.clientX - topologyPositions[id].x;
    startY = e.clientY - topologyPositions[id].y;
    viewport.style.cursor = "grabbing";
  });

  window.addEventListener("mousemove", function(e) {
    if (!isDragging) return;
    topologyPositions[id].x = e.clientX - startX;
    topologyPositions[id].y = e.clientY - startY;
    applyTransform(id);
  });

  window.addEventListener("mouseup", function() {
    if (isDragging) {
      isDragging = false;
      viewport.style.cursor = "grab";
    }
  });

  viewport.addEventListener("wheel", function(e) {
    if (e.ctrlKey || e.metaKey) {
      e.preventDefault();
      var factor = e.deltaY < 0 ? 1.1 : 0.9;
      zoomTopology(id, factor);
    }
  }, { passive: false });
}

function applyTransform(id) {
  var viewport = document.getElementById("viewport-" + id);
  if (!viewport) return;
  var mermaidEl = viewport.querySelector(".mermaid");
  if (!mermaidEl) return;

  var scale = topologyScales[id] || 1.0;
  var pos = topologyPositions[id] || { x: 0, y: 0 };
  mermaidEl.style.transform = "translate(" + pos.x + "px, " + pos.y + "px) scale(" + scale + ")";
}

function zoomTopology(id, factor) {
  if (!topologyScales[id]) topologyScales[id] = 1.0;
  topologyScales[id] = Math.max(0.3, Math.min(3.0, topologyScales[id] * factor));
  applyTransform(id);
}

function resetTopology(id) {
  topologyScales[id] = 1.0;
  topologyPositions[id] = { x: 0, y: 0 };
  applyTransform(id);
}

function toggleFullscreenTopology(cardId) {
  var card = document.getElementById(cardId);
  if (!card) return;
  if (!document.fullscreenElement) {
    if (card.requestFullscreen) {
      card.requestFullscreen();
    }
  } else {
    if (document.exitFullscreen) {
      document.exitFullscreen();
    }
  }
}

document.addEventListener("DOMContentLoaded", initMermaidTopology);
document.addEventListener("htmx:afterSwap", initMermaidTopology);
