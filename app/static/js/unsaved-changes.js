// Warnung bei ungespeicherten Aenderungen in Formularen.
// Setzt ein dirty-Flag bei input/change/select, setzt es bei submit zurueck.
(function () {
  var dirty = false;

  document.addEventListener("DOMContentLoaded", function () {
    var forms = document.querySelectorAll("form[method='POST'], form[method='post']");
    forms.forEach(function (form) {
      // Skip delete forms (inline, display:inline) und wizard step forms (bereits navigiert)
      if (form.style.display === "inline" || form.classList.contains("no-dirty-check")) return;

      form.addEventListener("input", function () { dirty = true; });
      form.addEventListener("change", function () { dirty = true; });
      form.addEventListener("submit", function () { dirty = false; });
    });
  });

  window.addEventListener("beforeunload", function (e) {
    if (dirty) {
      e.preventDefault();
      e.returnValue = "";
    }
  });
})();
