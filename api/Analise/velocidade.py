import cv2
import numpy as np
from ultralytics import YOLO
from collections import deque, defaultdict
import math
import time


# ============================================================
# RASTREADOR DE VEICULOS COM TRAJETORIA
# ============================================================

class RastreadorVeiculos:

    def __init__(self, max_historico=40):
        self.veiculos = {}
        self.proximo_id = 0
        self.max_historico = max_historico

        # Aumentado (antes 120)
        self.distancia_maxima = 250

        # Novo: tolerância a perda de deteção
        self.frames_perdidos_max = 120

    def atualizar(self, detecoes, frame_num):

        veiculos_ativos = []
        usados = set()

        # =========================
        # ASSOCIAR VEÍCULOS EXISTENTES
        # =========================
        for vid, dados in self.veiculos.items():

            ultimo = dados["ultimo_centro"]
            melhor_dist = float("inf")
            melhor_idx = None

            for i, det in enumerate(detecoes):

                if i in usados:
                    continue

                cx, cy = det["centro"]
                dist = math.hypot(cx - ultimo[0], cy - ultimo[1])

                if dist < melhor_dist and dist < self.distancia_maxima:
                    melhor_dist = dist
                    melhor_idx = i

            if melhor_idx is not None:

                det = detecoes[melhor_idx]
                usados.add(melhor_idx)

                centro = det["centro"]

                dados["centros"].append(centro)
                dados["ultimo_centro"] = centro
                dados["bbox"] = det["bbox"]
                dados["ultimo_frame"] = frame_num

                veiculos_ativos.append(vid)

        # =========================
        # CRIAR NOVOS VEÍCULOS
        # =========================
        for i, det in enumerate(detecoes):

            if i not in usados:

                vid = self.proximo_id
                self.proximo_id += 1

                self.veiculos[vid] = {
                    "centros": deque([det["centro"]], maxlen=self.max_historico),
                    "ultimo_centro": det["centro"],
                    "bbox": det["bbox"],
                    "ultimo_frame": frame_num
                }

                veiculos_ativos.append(vid)

        # =========================
        # REMOVER VEÍCULOS PERDIDOS
        # =========================
        remover = []

        for vid, dados in self.veiculos.items():
            if frame_num - dados["ultimo_frame"] > self.frames_perdidos_max:
                remover.append(vid)

        for vid in remover:
            del self.veiculos[vid]

        return veiculos_ativos

    def get(self, vid):
        return self.veiculos.get(vid)


# ============================================================
# CALCULO DE VELOCIDADE
# ============================================================

class CalculadorVelocidade:
    """
    Calcula velocidade baseada na trajetória do veículo.
    Converte deslocamento em pixels para km/h.
    """

    def __init__(self):
        self.fps = 30
        self.escala = None

    def configurar_fps(self, fps):
        if fps and fps > 1:
            self.fps = fps

    def auto_calibrar(self, largura_pixels, largura_real_m=7.0):
        if largura_pixels > 0:
            self.escala = largura_real_m / largura_pixels

    def calcular(self, centros):

        if len(centros) < 2:
            return 0

        if self.escala is None:
            return 0

        distancia_pixels = 0

        for i in range(1, len(centros)):
            x1, y1 = centros[i - 1]
            x2, y2 = centros[i]
            distancia_pixels += math.hypot(x2 - x1, y2 - y1)

        distancia_m = distancia_pixels * self.escala
        tempo = len(centros) / self.fps

        if tempo == 0:
            return 0

        velocidade_ms = distancia_m / tempo
        velocidade_kmh = velocidade_ms * 3.6

        return velocidade_kmh


# ============================================================
# DETETOR DE EXCESSO DE VELOCIDADE
# ============================================================

class DetetorExcessoVelocidade:

    def __init__(self, limite_kmh=60):
        self.limite = limite_kmh
        self.frames_confirmacao = 5
        self.historico = defaultdict(int)
        self.infratores = set()

    def verificar(self, veiculo_id, velocidade):

        if velocidade <= 0:
            return False

        if velocidade > self.limite:
            self.historico[veiculo_id] += 1
        else:
            self.historico[veiculo_id] = 0

        if self.historico[veiculo_id] >= self.frames_confirmacao:
            self.infratores.add(veiculo_id)
            return True

        return False


# ============================================================
# DETETOR SIMPLES DE FAIXA (CALIBRACAO)
# ============================================================

class DetetorFaixaSimples:

    def calcular_largura_via(self, frame):
        h, w = frame.shape[:2]
        return int(w * 0.4)


# ============================================================
# PROCESSAMENTO DO VIDEO
# ============================================================

def processar_video(caminho=None):

    import os
    from datetime import datetime

    modelo = YOLO("yolov8n.pt")

    if caminho:
        cap = cv2.VideoCapture(caminho)
    else:
        cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Erro ao abrir video")
        return

    # ===============================
    # CRIAR PASTA E VIDEO
    # ===============================
    os.makedirs("videos_processados", exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"videos_processados/velocidade_{timestamp}.mp4"

    largura = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    altura = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps_video = cap.get(cv2.CAP_PROP_FPS)

    if fps_video <= 0:
        fps_video = 30

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_path, fourcc, fps_video, (largura, altura))

    print(f" Video será salvo em: {output_path}")

    # ===============================
    # SISTEMAS
    # ===============================
    rastreador = RastreadorVeiculos()
    velocidade = CalculadorVelocidade()
    faixa = DetetorFaixaSimples()
    detetor_excesso = DetetorExcessoVelocidade(60)

    velocidade.configurar_fps(fps_video)

    frame_num = 0
    start = time.time()

    while True:

        ret, frame = cap.read()
        if not ret:
            break

        frame_num += 1

        largura_pixels = faixa.calcular_largura_via(frame)
        velocidade.auto_calibrar(largura_pixels)

        resultados = modelo(frame, classes=[2, 3, 5, 7])

        detecoes = []

        for r in resultados[0]:

            #  FILTRO DE CONFIANÇA
            conf = float(r.boxes.conf[0].cpu().numpy())
            if conf < 0.4:
                continue

            x1, y1, x2, y2 = r.boxes.xyxy[0].cpu().numpy().astype(int)
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2

            detecoes.append({
                "centro": (cx, cy),
                "bbox": (x1, y1, x2, y2)
            })

        ativos = rastreador.atualizar(detecoes, frame_num)

        for vid in ativos:

            dados = rastreador.get(vid)
            if dados is None:
                continue

            centros = list(dados["centros"])
            vel = velocidade.calcular(centros)
            excesso = detetor_excesso.verificar(vid, vel)

            x1, y1, x2, y2 = dados["bbox"]

            cor = (0, 0, 255) if excesso else (0, 255, 0)

            cv2.rectangle(frame, (x1, y1), (x2, y2), cor, 2)

            cv2.putText(frame, f"ID {vid}", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

            cv2.putText(frame, f"{vel:.1f} km/h", (x1, y1 - 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

            if excesso:
                cv2.putText(frame, "EXCESSO VELOCIDADE", (x1, y1 - 55),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

            # Trajetória
            for i in range(1, len(centros)):
                cv2.line(frame, centros[i - 1], centros[i], (255, 0, 0), 2)

        fps = frame_num / (time.time() - start)

        cv2.putText(frame, f"FPS {fps:.1f}", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        #  GUARDAR FRAME
        writer.write(frame)

        cv2.imshow("Sistema de Velocidade", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    writer.release()
    cv2.destroyAllWindows()

    print(" Processamento concluído")
    print(f" Video salvo em: {output_path}")

# ============================================================
# MAIN
# ============================================================

def main_velocidade(caminho=None):


        processar_video(caminho)
   


# ============================================================
# ASSINATURA
# ============================================================
# @module: vehicle_speed_system
# @author: kenny
# @method: trajectory_tracking_velocity
# @feature: speed_limit_detection
# @version: 2.0