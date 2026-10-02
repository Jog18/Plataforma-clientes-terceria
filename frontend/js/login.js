// Pantalla de inicio de sesión: manda usuario y contraseña a /api/login y,
// si todo va bien, pasa al dashboard. Los mensajes del servidor se muestran
// con textContent (nunca innerHTML) para que ningún texto se interprete como
// código.

(function () {
  "use strict";

  var form = document.getElementById("form");
  var usuario = document.getElementById("usuario");
  var contrasena = document.getElementById("contrasena");
  var aviso = document.getElementById("aviso");
  var boton = document.getElementById("entrar");

  function mostrar(texto, tipo) {
    aviso.textContent = texto;
    aviso.className = "aviso " + tipo;
    aviso.hidden = false;
  }

  function ocultar() {
    aviso.hidden = true;
    aviso.textContent = "";
  }

  // Si ya hay sesión abierta (por ejemplo, el usuario volvió con "atrás"),
  // no tiene caso mostrar el formulario.
  fetch("/api/yo", { credentials: "same-origin" })
    .then(function (r) { if (r.ok) { window.location.replace("/"); } })
    .catch(function () { /* sin red: el formulario sigue disponible */ });

  form.addEventListener("submit", function (evento) {
    evento.preventDefault();
    ocultar();

    var u = usuario.value.trim();
    var c = contrasena.value;
    if (!u || !c) {
      mostrar("Escribe tu usuario y tu contraseña.", "error");
      (u ? contrasena : usuario).focus();
      return;
    }

    boton.disabled = true;
    boton.textContent = "Entrando…";

    fetch("/api/login", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ usuario: u, contrasena: c })
    })
      .then(function (r) {
        if (r.ok) {
          window.location.replace("/");
          return;
        }
        return r.json().catch(function () { return {}; }).then(function (datos) {
          var detalle = typeof datos.detail === "string" ? datos.detail : "";
          if (r.status === 429) {
            mostrar(detalle || "Demasiados intentos. Espera unos minutos.", "alerta");
          } else if (r.status === 401 || r.status === 422) {
            mostrar("Usuario o contraseña incorrectos.", "error");
          } else {
            mostrar("No se pudo iniciar sesión (" + r.status + "). Intenta de nuevo.", "error");
          }
          contrasena.value = "";
          contrasena.focus();
        });
      })
      .catch(function () {
        mostrar("No hay conexión con el servidor. Revisa tu red e intenta de nuevo.", "error");
      })
      .then(function () {
        boton.disabled = false;
        boton.textContent = "Entrar";
      });
  });
})();
