# Análise dos algoritmos de deteção de vídeo (2026-09-04)

Análise dos 3 módulos de deteção (`api/Analise/Contramao.py`, `parado.py`,
`velocidade.py`, já corrigidos para funcionarem em background/Celery) — sugestões
de desenho e otimização de tempo de processamento. Nada disto foi aplicado
ainda; fica registado para discussão e priorização.

## Onde vai o tempo de processamento

A causa dominante é a inferência YOLO por frame em CPU — `requirements.txt`
fixa `torch==2.13.0+cpu`, não há GPU disponível, e é aí que está o grosso do
custo, não na lógica de tracking (O(n·m) com poucos veículos, irrelevante).

- **`velocidade.py` corre YOLO no frame em resolução total**, enquanto
  `parado.py` e `Contramao.py` já reduzem para 640×360 antes de detetar e só
  reescalam as coordenadas depois. Alinhar `velocidade.py` ao mesmo padrão dos
  outros dois é provavelmente o ganho de performance mais imediato (requer
  recalibrar `auto_calibrar`, que hoje mede pixels no frame a full-res).
- **O modelo YOLO é recarregado do disco a cada denúncia processada**
  (`YOLO("yolov8n.pt")` dentro de cada função `processar_video*`). Num worker
  Celery persistente, devia ser carregado uma vez por processo (singleton a
  nível de módulo, ou `worker_process_init` do Celery) em vez de a cada task.
- **Todos os frames são processados** — nenhum dos três faz frame-skipping.
  Processar 1 em cada 2–3 frames e interpolar a posição do tracker nos frames
  saltados costuma cortar o tempo total a metade ou mais, com perda de
  precisão mínima para tráfego normal.
- Depois da deteção há uma **segunda passagem via `ffmpeg`**
  (`converter_video_para_browser`) para reencodar para H.264 — necessária
  porque `cv2.VideoWriter` com `mp4v`/`XVID` não é fiável em browsers, mas é
  custo extra. `-preset veryfast` em vez de `-preset fast` reduz esse tempo
  com perda de qualidade insignificante para vídeo de vigilância.

## Desenho dos algoritmos

- Os três módulos reimplementam **trackers quase idênticos** (correspondência
  pelo centróide mais próximo, sem previsão de movimento) — frágil quando dois
  veículos se cruzam ou há oclusão momentânea (o ID pode trocar). Melhoria
  simples: prever a posição seguinte com base na velocidade do frame anterior
  (modelo de velocidade constante) antes do matching, sem precisar de Kalman
  filter completo.
- Extrair um **tracker partilhado único** (usado pelos três) evitaria a
  duplicação atual e propagaria qualquer correção/otimização futura a todos
  de uma vez — relevante também para uma futura deteção de acidente.
- A **calibração de velocidade** em `velocidade.py` assume que 40% da largura
  do frame equivale a 7 metros de via — valor fixo, não calibrado por
  câmara/ângulo/zoom. Os km/h reportados podem estar substancialmente errados
  consoante a instalação da câmara; vale a pena documentar como estimativa
  aproximada até existir calibração por câmara.
- Limiares como `frames_confirmacao=5` ou `distancia_maxima=250px` estão
  fixos em nº de frames/pixels, não em tempo real — um vídeo a 15fps confirma
  uma infração 2x mais devagar que um a 30fps. Derivá-los do `fps` real
  (ex: `frames_confirmacao = int(fps * 0.2)`) tornaria o comportamento
  consistente entre vídeos.

## Prioridade sugerida (esforço vs. ganho)

1. Alinhar `velocidade.py` à deteção em resolução reduzida — mudança pequena, maior ganho.
2. Cache do modelo YOLO por worker Celery (evitar reload por task).
3. Frame-skipping com interpolação do tracker.
4. Tracker partilhado único, com previsão de movimento.
