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
- **Confiança real na análise de vídeo** (antes fixa em `0.85` sempre, independentemente do resultado): `ResultadoAnaliseService.executar_analise` passa a receber `confianca` calculada a partir da confiança média das deteções YOLO nos veículos que geraram alerta (ou `0.5` quando não há alerta — neutro, sem evidência positiva nem negativa). Aplicado a `Contramao.py`, `velocidade.py` e `parado.py`.
- **Bug crítico corrigido em `parado.py`:** o alerta de "veículo parado" só disparava com `esta_parado AND em_zona`, mas zonas proibidas só podiam ser definidas interativamente com o rato — impossível em modo headless (worker Celery). Ou seja, a deteção de veículo parado nunca validava nenhuma denúncia em produção. Alerta passa a disparar por `esta_parado` sozinho (zona passa a ser informativa, não obrigatória). _(commit `f2e172e`)_
- **Filtro de confiança YOLO padronizado** (≥0.4) em `Contramao.py` e `parado.py`, igual a `velocidade.py`; e tratamento de erro por frame (uma exceção num frame mau já não aborta o vídeo inteiro nem obriga o Celery a repetir tudo). _(commit `f2e172e`)_
- **Validação de tamanho de vídeo no upload de denúncia** (máx. 100MB, `DENUNCIA_VIDEO_MAX_SIZE_MB`) — pensado para dados móveis limitados; corrigido também um bug em que a denúncia era criada na BD antes de validar o ficheiro, deixando registos órfãos em uploads inválidos. Validação replicada no frontend (`CriarDenuncia.tsx`) para poupar dados do cidadão. _(commits `753ffd4` backend / frontend a seguir)_
- **Ranking anónimo de cidadãos mais ativos** — `Cidadao.numero_denuncias` passa a ser incrementado de verdade (nunca tinha sido); novo `GET /cidadao/user/ranking/` com top 10. Decisão de segurança tomada com o utilizador: **nunca mostra nomes**, cada cidadão recebe um código estável e não-reversível (hash truncado do ID); o próprio cidadão vê o seu código no perfil para se reconhecer no ranking, sem que outros o consigam identificar. _(commit `917df0e` backend / frontend a seguir)_

### ⏳ Por fazer (identificado mas não priorizado ainda)

- ~~Reconhecimento automático de matrícula (ALPR/OCR)~~ — **rejeitado pelo utilizador** (2026-09-04): a qualidade da câmara do telemóvel do cidadão é demasiado variável/imprevisível para dar leituras fiáveis; geraria falsos negativos constantes e falsa expectativa de verificação automática. Não avançar.
- **Geolocalização nas denúncias** (lat/lng capturada no telemóvel do cidadão ao criar a denúncia, em vez de só texto livre em `localizacao`). Desbloqueia um mapa real de infrações para Super Admin/PT e resolve o "agente mais próximo" pendente para o SMS de acidente de viação (ver item abaixo). Custo: migração no modelo, pedir permissão de localização no browser, lib de mapas (Leaflet, sem chave paga).
- Análise dos 3 algoritmos de deteção feita e registada em [`docs/ANALISE_ALGORITMOS_VIDEO.md`](ANALISE_ALGORITMOS_VIDEO.md) — nenhuma sugestão aplicada ainda, por priorizar/discutir.
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
