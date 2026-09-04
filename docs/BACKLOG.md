# Backlog SGDIT (Backend + Frontend)

Registo de tudo o que é feito na aplicação (backend `SGDIT_Backend` e frontend
`SBDIT_Frontend_TS`), sessão a sessão. Atualizar sempre que uma tarefa for
concluída, iniciada ou identificada.

Legenda: ✅ concluído · 🔄 em progresso · ⏳ por fazer

---

## 2026-09-04

### ✅ Concluído

- **Backend** — fix na deteção de linhas em `api/Analise/Contramao.py` (extração de coordenadas), deps do celery/redis adicionadas a `requirements.txt`, correção do caminho do venv em `start.sh`. _(commit `2ab066d`)_
- **Backend** — recuperação de senha para todos os utilizadores (papel único `Utilizador`, serve Cidadão/PT/Admin/Super Admin):
  - `POST /api/auth/password-reset/` — pede email, gera token (`PasswordResetTokenGenerator`), envia link por email.
  - `POST /api/auth/password-reset/confirm/` — recebe `uid` + `token` + nova password, valida e altera.
  - `EMAIL_BACKEND` de consola (dev) e `FRONTEND_URL` configuráveis via `.env`.
  - Erro de email duplicado no registo de cidadão tratado com 400 (antes rebentava com 500). _(commit `7fcd2aa`)_
- **Frontend** — `src/utils/validationSchemas.ts` criado: regex e schemas zod partilhados (nome, email, password forte, telefone `+244`, matrícula `AB-12-CD`, código legal, número de agente, posto, localização, descrição), para reutilizar em todos os formulários.

### 🔄 Em progresso

- **Frontend** — Signup do cidadão (`SignupPage.jsx` está vazio, a converter para `.tsx` com validação zod/regex).
- **Frontend** — Páginas de recuperação de senha (pedir email + redefinir com token) e respetivas rotas em `AppRoutes.tsx`.
- **Frontend** — Aplicar as regex de `validationSchemas.ts` aos formulários já existentes: `LoginPage.tsx`, `cidadao/CidadaoPerfil.tsx`, `cidadao/CriarDenuncia.tsx`, `Admin/Policias.tsx`, `SuperAdmin/Admins.tsx`, `PT/DetalhesDenunciaPt.tsx`.

### ⏳ Por fazer (identificado mas não priorizado ainda)

- **Módulo Super Admin** (pausado a pedido do utilizador para dar prioridade ao signup/recuperação de senha):
  - `SuperAdminViewSet` (em `admin_controller.py`) não está registado em `api/urls.py`.
  - Bug em `listar_cidadaos`: loop usa `cidadao.id` (a lista) em vez de `c.id` (o item).
  - `api/controller/superadmin_controller.py` e `evidencia_controller.py` estão vazios (ficheiros mortos).
  - Faltam endpoints de listagem global para o Super Admin (todos os PTs, todas as denúncias, todos os cidadãos) e ação de ativar/desativar cidadão.
  - Frontend: `superAdminService.ts` chama rotas que não existem (`/cidadao/lista/`, `/pts/lista/`, `/denuncia/lista/`).
  - Frontend: páginas `SuperAdmin/Cidadaos.tsx`, `Denuncias.tsx`, `Policiais.tsx` ainda usam dados mock.
  - `Relatorios.tsx` (gráficos/analytics) não tem endpoint de agregação no backend — mock.
- **Bugs/limpeza transversais no frontend:**
  - `useAuth.isAuthenticated()` lê `localStorage.getItem("token")`, mas o login guarda a chave `"access"` — nunca autentica por essa via (afeta `ProtectedRoute.tsx`, que parece não estar em uso — `AppRoutes.tsx` usa `RouteGuard.tsx`).
  - `authService.refreshToken()` usa caminho relativo errado (`/api/auth/token/refresh/`, que não existe); o correto é `/api/token/refresh/` (já certo no interceptor do `axios.ts`).
  - `AuthContext.jsx` vazio e não importado em lado nenhum — ficheiro morto.
  - `Admin/Policiais2.tsx` é um stub antigo com mock data, substituído por `Policias.tsx` — ficheiro morto.
  - `ptService.ts` tem `alert()` de debug esquecidos em `listarPT` e `criarPT`.
  - Mistura de `.jsx`/`.tsx` num projeto TS (`Navbar.jsx`, `Sidebar.jsx`, `Home/index.jsx`, `colors.js`).
