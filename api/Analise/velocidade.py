import cv2
import numpy as np
from ultralytics import YOLO
from collections import deque, defaultdict
import math
import time
import os
from datetime import datetime
from api.helper.videoConvert import converter_video_para_browser
from api.service.resultado_analise_service import ResultadoAnaliseService
from api.model.analise import ResultadoAnalise
from api.Analise.modelo import obter_modelo
from api.helper.videoPreprocess import preprocessar_video
from django.conf import settings


# ============================================================
# RASTREADOR DE VEICULOS COM TRAJETORIA
# ============================================================

class RastreadorVeiculos:

    def __init__(self, max_historico=40):
        self.veiculos = {}
        self.proximo_id = 0
        self.max_historico = max_historico
        self.distancia_maxima = 250
        self.frames_perdidos_max = 120

    def atualizar(self, detecoes, frame_num):

        veiculos_ativos = []
        usados = set()

        # Associar veículos existentes
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
                dados["confianca"] = det.get("confianca", dados.get("confianca", 0))

                veiculos_ativos.append(vid)

        # Criar novos veículos
        for i, det in enumerate(detecoes):

            if i not in usados:

                vid = self.proximo_id
                self.proximo_id += 1

                self.veiculos[vid] = {
                    "centros": deque([det["centro"]], maxlen=self.max_historico),
                    "ultimo_centro": det["centro"],
                    "bbox": det["bbox"],
                    "ultimo_frame": frame_num,
                    "confianca": det.get("confianca", 0)
                }

                veiculos_ativos.append(vid)

        # Remover veículos perdidos
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
# DETETOR DE EXCESSO DE VELOCIDADE (COM ALERTAS)
# ============================================================

class DetetorExcessoVelocidade:

    def __init__(self, limite_kmh=60, fps=30):
        self.limite = limite_kmh
        # equivalente a 5 frames a 30fps (~0.17s) - calculado a partir do fps
        # real do vídeo para que reduzir o fps no pré-processamento não altere
        # o tempo necessário para confirmar a infração
        self.frames_confirmacao = max(1, round((fps or 30) / 6))
        self.historico = defaultdict(int)
        self.alertas_enviados = set()  # ← NOVO: guarda IDs que já alertaram
        self.total_alertas = 0          # ← NOVO: contador total de alertas

    def verificar(self, veiculo_id, velocidade, frame_num):

        if velocidade <= 0:
            return False

        if velocidade > self.limite:
            self.historico[veiculo_id] += 1
        else:
            self.historico[veiculo_id] = 0

        if self.historico[veiculo_id] >= self.frames_confirmacao:
            # Verificar se já não enviamos alerta para este veículo
            if veiculo_id not in self.alertas_enviados:
                self.alertas_enviados.add(veiculo_id)
                self.total_alertas += 1
                print(f"\n⚠️ ALERTA ENVIADO! Veículo {veiculo_id} em EXCESSO DE VELOCIDADE ({velocidade:.1f} km/h) no frame {frame_num}")
                return True
            else:
                # Veículo já alertou, não repetir
                return True  # Ainda está em excesso, mas sem novo alerta
        return False
    
    def get_total_alertas(self):
        return self.total_alertas
    
    def get_alertas_enviados(self):
        return self.alertas_enviados


# ============================================================
# DETETOR SIMPLES DE FAIXA (CALIBRACAO)
# ============================================================

class DetetorFaixaSimples:

    def calcular_largura_via(self, frame):
        h, w = frame.shape[:2]
        return int(w * 0.4)


# ============================================================
# PROCESSAMENTO DO VIDEO (COM CONTAGEM DE ALERTAS)
# ============================================================

def processar_video(caminho, denuncia, salvar_video=True, limite_kmh=60):

    modelo = obter_modelo()

    if caminho and not os.path.isabs(caminho):
        caminho = os.path.join(settings.MEDIA_ROOT, caminho)

    caminho_original = caminho

    if caminho:
        caminho = preprocessar_video(caminho)

    if caminho:
        cap = cv2.VideoCapture(caminho)
        print(f"📁 Vídeo: {caminho}")
    else:
        cap = cv2.VideoCapture(0)
        print("📹 Webcam")

    if not cap.isOpened():
        print("❌ Erro ao abrir video")
        return

    # ===============================
    # CRIAR PASTA E VIDEO
    # ===============================
    output_dir = os.path.join(settings.MEDIA_ROOT, "videos_processados")
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if caminho:
        nome_base = os.path.splitext(os.path.basename(caminho))[0]
        output_path = f"{output_dir}/{nome_base}_velocidade_{timestamp}.mp4"
    else:
        output_path = f"{output_dir}/webcam_velocidade_{timestamp}.mp4"

    largura = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    altura = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps_video = cap.get(cv2.CAP_PROP_FPS)

    if fps_video <= 0:
        fps_video = 30

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_path, fourcc, fps_video, (largura, altura))

    print(f"💾 Vídeo será salvo em: {output_path}")

    # ===============================
    # SISTEMAS
    # ===============================
    rastreador = RastreadorVeiculos()
    velocidade = CalculadorVelocidade()
    faixa = DetetorFaixaSimples()
    detetor_excesso = DetetorExcessoVelocidade(limite_kmh, fps=fps_video)

    velocidade.configurar_fps(fps_video)

    frame_num = 0
    start = time.time()
    confiancas_alertas = []

    print(f"\n🚦 Limite de velocidade: {detetor_excesso.limite} km/h")
    print("\n🎬 PROCESSANDO (modo automático, sem interface gráfica)...")
    print("-"*50)

    while True:

        ret, frame = cap.read()
        if not ret:
            break

        frame_num += 1

        largura_pixels = faixa.calcular_largura_via(frame)
        velocidade.auto_calibrar(largura_pixels)

        # Deteção em resolução reduzida (mesmo padrão de Contramao.py/parado.py) —
        # YOLO em CPU é o maior custo de tempo; detetar a full-res não traz mais
        # precisão que compense o tempo extra
        frame_pequeno = cv2.resize(frame, (640, 360))
        escala_x = frame.shape[1] / 640
        escala_y = frame.shape[0] / 360

        try:
            resultados = modelo(frame_pequeno, classes=[2, 3, 5, 7])
        except Exception as e:
            print(f"⚠️ Erro ao processar frame {frame_num}, a saltar: {e}")
            resultados = None

        detecoes = []

        if resultados and len(resultados) > 0:
            for r in resultados[0]:

                conf = float(r.boxes.conf[0].cpu().numpy())
                if conf < 0.4:
                    continue

                x1, y1, x2, y2 = r.boxes.xyxy[0].cpu().numpy().astype(int)

                x1 = int(x1 * escala_x)
                y1 = int(y1 * escala_y)
                x2 = int(x2 * escala_x)
                y2 = int(y2 * escala_y)

                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2

                detecoes.append({
                    "centro": (cx, cy),
                    "bbox": (x1, y1, x2, y2),
                    "confianca": conf
                })

        ativos = rastreador.atualizar(detecoes, frame_num)

        # Contar veículos em excesso neste frame
        excessos_frame = 0

        for vid in ativos:

            dados = rastreador.get(vid)
            if dados is None:
                continue

            centros = list(dados["centros"])
            vel = velocidade.calcular(centros)
            total_antes = len(detetor_excesso.alertas_enviados)
            excesso = detetor_excesso.verificar(vid, vel, frame_num)

            if len(detetor_excesso.alertas_enviados) > total_antes:
                confiancas_alertas.append(dados.get("confianca", 0))

            if excesso:
                excessos_frame += 1

            x1, y1, x2, y2 = dados["bbox"]

            cor = (0, 0, 255) if excesso else (0, 255, 0)

            cv2.rectangle(frame, (x1, y1), (x2, y2), cor, 2)

            cv2.putText(frame, f"ID {vid}", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

            cv2.putText(frame, f"{vel:.1f} km/h", (x1, y1 - 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

            if excesso:
                cv2.putText(frame, "⚠️ EXCESSO VELOCIDADE", (x1, y1 - 55),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

            # Trajetória
            for i in range(1, len(centros)):
                cv2.line(frame, centros[i - 1], centros[i], (255, 0, 0), 2)

        fps = frame_num / (time.time() - start)

        # ===============================
        # INFORMAÇÕES NO ECRÃ (COM ALERTAS)
        # ===============================
        cv2.putText(frame, f"Frame: {frame_num}", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, f"FPS: {fps:.1f}", (20, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(frame, f"Veiculos: {len(ativos)}", (20, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        cv2.putText(frame, f"Excesso agora: {excessos_frame}", (20, 130),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # ← NOVO: Mostrar total de alertas enviados
        cv2.putText(frame, f"Alertas enviados: {detetor_excesso.get_total_alertas()}", (20, 160),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 165, 0), 2)
        
        # Mostrar limite de velocidade
        cv2.putText(frame, f"Limite: {detetor_excesso.limite} km/h", (frame.shape[1] - 200, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)

        # GUARDAR FRAME
        writer.write(frame)

    cap.release()
    writer.release()

    if caminho != caminho_original and os.path.exists(caminho):
        os.remove(caminho)

    video_browser = converter_video_para_browser(output_path)

    print(f"\n Processamento concluído!")
    print(f" Video salvo em: {output_path}")
    print(f" TOTAL DE ALERTAS DE EXCESSO DE VELOCIDADE: {detetor_excesso.get_total_alertas()}")
    print(f"Veículos únicos: {rastreador.proximo_id}")
    alertas=detetor_excesso.get_total_alertas()
    confianca_final = round(sum(confiancas_alertas) / len(confiancas_alertas), 2) if confiancas_alertas else 0.5

    analise = ResultadoAnaliseService.executar_analise(denuncia, video_browser or output_path, alertas, confianca_final)

    return analise


# ============================================================
# MAIN
# ============================================================

def main_velocidade(path,denuncia):


    analise = processar_video(path, denuncia, salvar_video=True)
    return analise


