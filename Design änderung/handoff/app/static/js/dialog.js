// Dialoge: öffnen über [data-dialog-open="id"], schließen über [data-dialog-close],
// Klick auf den Hintergrund oder Escape.
(function () {
  function close(el) { if (el) el.classList.remove("open"); }

  document.addEventListener("click", function (e) {
    var opener = e.target.closest("[data-dialog-open]");
    if (opener) {
      e.preventDefault();
      var target = document.getElementById(opener.dataset.dialogOpen);
      if (target) target.classList.add("open");
      return;
    }

    if (e.target.closest("[data-dialog-close]")) {
      e.preventDefault();
      close(e.target.closest(".dialog-backdrop"));
      return;
    }

    if (e.target.classList && e.target.classList.contains("dialog-backdrop")) close(e.target);
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      document.querySelectorAll(".dialog-backdrop.open").forEach(close);
    }
  });
})();
