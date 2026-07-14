
(function () {
    var buttons = document.querySelectorAll(".ranking-toggle-button");
    var individual = document.getElementById("ranking-individual");
    var familiar = document.getElementById("ranking-familiar");
    if (!buttons.length || !individual || !familiar) return;

    buttons.forEach(function (button) {
        button.addEventListener("click", function () {
            var mostrarFamiliar = button.getAttribute("data-ranking-target") === "familiar";
            individual.hidden = mostrarFamiliar;
            familiar.hidden = !mostrarFamiliar;
            buttons.forEach(function (item) {
                var activo = item === button;
                item.classList.toggle("is-active", activo);
                item.setAttribute("aria-pressed", activo ? "true" : "false");
            });
        });
    });
})();
