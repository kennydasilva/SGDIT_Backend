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
- **Backend** — signup de cidadão passa a aceitar `numero` (telefone) opcional no registo.
- **Frontend** — `fix: remover entrada inválida tailwindcss/vite do package.json` (alteração pendente de sessão anterior, commitada à parte). _(commit `4cc59c9`)_
- **Frontend** — Signup do cidadão (`SignupPage.tsx`, antes vazio) com validação zod/regex (nome, email, telefone `+258`, senha forte), ligado ao endpoint `/cidadaos/registrar/` já existente.
- **Frontend** — Recuperação de senha: `RecuperarSenhaPage.tsx` (pedir email) + `RedefinirSenhaPage.tsx` (nova senha via link), rotas `/cadastrar`, `/recuperar-senha`, `/redefinir-senha/:uid/:token` em `AppRoutes.tsx`.
- **Frontend** — `authService.ts`: novas funções `requestPasswordReset`/`confirmPasswordReset`; corrigido `refreshToken` (apontava para rota inexistente `/api/auth/token/refresh/`).
- **Frontend** — `LoginPage.tsx`: links para cadastro/recuperação via `Link` do react-router (antes `<a href>` morto, sem rota).
- **Frontend** — `src/utils/validationSchemas.ts` criado (regex/zod partilhados: nome, email, senha forte, telefone `+258 8XX XXX XXX` Moçambique, matrícula `AB-12-CD`, código legal, número de agente, posto, localização, descrição) e aplicado a `LoginPage`, `CidadaoPerfil`, `CriarDenuncia`, `Admin/Policias`, `SuperAdmin/Admins`, `PT/DetalhesDenunciaPt`. _(commits `67abc07`, `f984c40`)_
- Removidos ficheiros mortos: `SignupPage.jsx`, `LoginService.js`, `validators.js` (vazios, substituídos pelo novo signup e `validationSchemas.ts`).
- **Backend** — corrigidos `api/Analise/velocidade.py` e `api/Analise/parado.py`: removida toda a interação `cv2.imshow`/`cv2.waitKey`/`input()` (bloqueava/rebentava num worker Celery em background, sem ecrã nem terminal); caminhos de entrada/saída ancorados em `settings.MEDIA_ROOT`; vídeo convertido para formato compatível com browser (como já fazia `Contramao.py`); corrigido bug em `parado.py` onde o vídeo processado nunca era escrito (`out.write()`/`out.release()` em falta — ficheiro de saída ficava sempre vazio). _(commit `e8ef02f`)_
- **Módulo Super Admin completo:**
  - Backend: `SuperAdminViewSet` movido para `superadmin_controller.py` e registado em `api/urls.py` (nunca tinha estado ligado a nenhuma rota); corrigido bug em `listar_cidadaos` (loop usava `cidadao.id` da queryset em vez de `c.id`); novo `GET /cidadao/lista/` e `PATCH /cidadao/<id>/status/` (ativar/desativar); `GET /pts/` agora também acessível a `SUPER_ADMIN` (nova permissão `IsAdminOrSuperAdmin`); removido `evidencia_controller.py` (vazio, morto). _(commit `b0ac01c`)_
  - Frontend: `superAdminService.ts` corrigido para os endpoints reais; `Cidadaos.tsx`, `Denuncias.tsx`, `Policiais.tsx` deixam de usar mock e passam a consumir dados reais, com loading/erro. _(commit `40b08e6`)_
  - Limpeza: `AuthContext.jsx` (vazio, morto), `Admin/Policiais2.tsx` (stub mock morto), `alert()` de debug e import morto em `ptService.ts`. _(commit `c2bb321`)_
  - `authService.refreshToken()` (caminho relativo errado) já tinha sido corrigido antes, junto com o signup. _(commit `67abc07`)_

### ⏳ Por fazer (identificado mas não priorizado ainda)

- Analisar os 3 algoritmos de deteção (`Contramao.py`, `parado.py`, `velocidade.py`) e sugerir melhorias de desenho e otimização do tempo de processamento (pedido pelo utilizador).
- **Denúncia de "acidente de viação" (novo tipo) — decisão de desenho confirmada com o utilizador:**
  - **Não** passa pelo pipeline de análise de vídeo por IA (ao contrário de Contramão/Parado/Velocidade) — não há tempo para análise neste caso.
  - Fluxo correto: comunicação/reporte **direto** ao agente (PT) mais próximo.
  - Notificação deve ser por **SMS**, o que requer integração com **Firebase** (Cloud Messaging / alguma extensão de SMS) — ainda não configurada no projeto.
  - Falta também decidir como determinar o "agente mais próximo": os PTs só têm um campo `localizacao` em texto livre (`api/model/user.py`), sem coordenadas GPS — precisa de desenho antes de implementar.
  - **Por implementar quando a integração Firebase/SMS estiver disponível.** (Tentativa inicial de algoritmo de deteção por vídeo foi feita e descartada nesta sessão, por não corresponder ao fluxo pretendido.)
- `Relatorios.tsx` (gráficos/analytics do Super Admin) não tem endpoint de agregação no backend — continua mock.
- **Bugs/limpeza transversais no frontend ainda por fazer:**
  - `useAuth.isAuthenticated()` lê `localStorage.getItem("token")`, mas o login guarda a chave `"access"` — nunca autentica por essa via (afeta `ProtectedRoute.tsx`, que parece não estar em uso — `AppRoutes.tsx` usa `RouteGuard.tsx`).
  - Mistura de `.jsx`/`.tsx` num projeto TS (`Navbar.jsx`, `Sidebar.jsx`, `Home/index.jsx`, `colors.js`).
