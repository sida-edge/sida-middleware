// auth/session.js
// Holds the session credentials strictly in memory (a closure variable), never
// touching disk, cookies, localStorage or sessionStorage. Cleared on logout.
export class Session {
  constructor() {
    this._username = null;
    this._password = null;
    this.status = "nao_autenticado"; // nao_autenticado | autenticando | autenticado | credenciais_invalidas
  }
  set(username, password) { this._username = username; this._password = password; }
  get username() { return this._username; }
  get password() { return this._password; }
  clear() { this._username = null; this._password = null; this.status = "nao_autenticado"; }
}
