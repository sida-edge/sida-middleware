// ui/login.js
// Login screen controller: collects user/password, shows the configured broker
// URL (read-only), and delegates the actual connect to the app bootstrap.
export class LoginView {
  constructor({ brokerUrl, onSubmit }) {
    this.onSubmit = onSubmit;
    this.form = document.getElementById("login-form");
    this.userEl = document.getElementById("username");
    this.passEl = document.getElementById("password");
    this.btn = document.getElementById("login-btn");
    this.errEl = document.getElementById("login-error");
    this.statusEl = document.getElementById("login-status");
    document.getElementById("broker-url").value = brokerUrl || "(não configurado)";

    this.form.addEventListener("submit", (e) => {
      e.preventDefault();
      this._submit();
    });
  }

  async _submit() {
    this.errEl.hidden = true;
    this.statusEl.hidden = false;
    this.statusEl.textContent = "Conectando ao broker…";
    this.btn.disabled = true;
    try {
      await this.onSubmit(this.userEl.value, this.passEl.value);
      // On success the app swaps views; clear the password field from the DOM.
      this.passEl.value = "";
    } catch (err) {
      this.showError(err);
    } finally {
      this.btn.disabled = false;
      this.statusEl.hidden = true;
    }
  }

  showError(err) {
    this.errEl.hidden = false;
    const msg = String(err && err.message || err || "");
    if (/credential|not authorized|bad user|password|code 4|code 5/i.test(msg)) {
      this.errEl.textContent = "Credenciais inválidas — verifique usuário e senha.";
    } else if (/websocket|econnrefused|failed to construct|network|timeout|closed/i.test(msg)) {
      this.errEl.textContent = "Não foi possível conectar ao endereço configurado.";
    } else {
      this.errEl.textContent = `Falha na conexão: ${msg}`;
    }
  }
}
