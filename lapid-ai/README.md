# Lapid.ai — Etapas 1 e 2: suporte, dashboard e monitoramento de erros

Widget de suporte incorporável, API de reclamações com protocolo e painel administrativo.
Ainda **não** inclui IA, GitHub nem autocorreção (Etapas 3 a 9). Identidade visual documentada em `docs/DESIGN.md`.

## Rodar (Codespaces/Linux/macOS)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
python scripts/hash_password.py        # cole a linha ADMIN_PASSWORD_HASH no .env e ajuste ADMIN_EMAIL
flask --app backend.app run --debug
```
## Rodar (Windows PowerShell)
```powershell
py -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
copy .env.example .env
python scripts\hash_password.py
flask --app backend.app run --debug
```
Abra `http://localhost:5000/admin`. No **Codespaces**, defina `PROXY_COUNT=1` no `.env` e use a URL encaminhada da porta 5000.

## Testar o widget
1. Entre no painel → **Sites** → conecte um site com o domínio `localhost` (no Codespaces, o host da URL encaminhada, ex.: `xxxx-5000.app.github.dev`).
2. Abra `/demo` (requer `ENABLE_DEMO=true`), clique em **Suporte** e envie um relato.
3. Veja o protocolo (`LPD-AAAAMMDD-0001`) e a reclamação em **Reclamações**.

Em sites reais, copie o código da página **Sites** e cole antes de `</body>`.

## Testes
```bash
pytest
```

## Segurança aplicada
- Segredos só via `.env`; senha do admin armazenada como hash.
- Login com limite de tentativas, sessão nova a cada login, CSRF em todo POST do painel.
- Rotas `/admin/*` protegidas, com CSP estrita e `no-store`.
- Widget autenticado por chave pública + verificação de origem (domínio/subdomínios do site) e rate limit.
- Validação de entrada, limite de 32 KB por requisição, saída escapada (anti-XSS).
- O widget envia apenas `origin + pathname` (sem query string, para não vazar tokens).

## Etapa 2: monitoramento de erros
- **Navegador**: o widget captura `error` e `unhandledrejection` do site (máx. 5 erros distintos por página, sem query strings; ignora extensões). Desligue com `data-monitor="false"`.
- **Servidor**: toda exceção não tratada do Lapid.ai é registrada (e enviada ao Sentry se `SENTRY_DSN` estiver definido).
- **Sentry (opcional)**: crie uma *Internal Integration* com webhook para `https://SEU-LAPID/api/monitor/sentry?site_id=ID`, evento *issue*, e coloque o *Client Secret* em `SENTRY_WEBHOOK_SECRET`. A assinatura HMAC é obrigatória.
- **Recorrência**: erros iguais são agrupados (números e query strings são ignorados na comparação). Um erro resolvido que volta **reabre sozinho**.
- **Alertas**: novo erro, regressão e recorrência (5, 25, 100, 500 ocorrências) geram atividade no painel, um contador na aba **Erros** e, se `ALERT_WEBHOOK_URL` existir, uma mensagem no Slack/Discord.
- Teste: abra `/demo` e use os botões "Provocar erro".

**Ainda falta da Etapa 2:** verificação periódica de disponibilidade dos sites (uptime), que exige um agendador em segundo plano.

## Próximo passo
Uptime dos sites e, depois, Etapa 3 (integração com a OpenAI API).
