import cv2
import numpy as np
from ultralytics import YOLO
from collections import defaultdict, deque
import math
import time
from datetime import datetime
from api.helper.videoConvert import converter_video_para_browser
from api.service.resultado_analise_service import ResultadoAnaliseService
from api.model.analise import ResultadoAnalise
from django.conf import settings
import os


# ============================================
# PARTE 1: RASTREADOR COM DETEÇÃO DE PARADOS
# ============================================

class RastreadorParados:
    """
    Rastreador que deteta veículos parados por muito tempo
    """
    def __init__(self, max_historico=100, fps=30):
        self.veiculos = {}
        self.proximo_id = 0
        self.cores = {}
        self.max_historico = max_historico
        
        # Melhorado (antes 100)
        self.distancia_maxima = 250
        
        self.fps = fps if fps > 0 else 30
        
        # Parâmetros para deteção de parados
        self.tempo_min_parado = 10
        self.distancia_min_movimento = 15
        
        # Novo: tolerância para perda temporária de deteção
        self.frames_perdidos_max = 120

    def atualizar(self, detecoes, frame_num, timestamp=None):
        """
        Atualiza rastreador com novas deteções
        """
        if timestamp is None:
            timestamp = time.time()

        veiculos_atuais = []
        detecoes_associadas = set()

        # ============================
        # ASSOCIAR DETEÇÕES EXISTENTES
        # ============================
        for veiculo_id, dados in self.veiculos.items():
            ultimo_centro = dados['ultimo_centro']

            melhor_dist = float('inf')
            melhor_det = None
            melhor_idx = -1

            for idx, det in enumerate(detecoes):
                if idx in detecoes_associadas:
                    continue

                centro = det['centro']

                dist = math.sqrt(
                    (ultimo_centro[0] - centro[0]) ** 2 +
                    (ultimo_centro[1] - centro[1]) ** 2
                )

                if dist < melhor_dist and dist < self.distancia_maxima:
                    melhor_dist = dist
                    melhor_det = det
                    melhor_idx = idx

            if melhor_det is not None:
                centro = melhor_det['centro']

                dados['centros'].append(centro)
                dados['ultimo_centro'] = centro
                dados['ultimo_frame'] = frame_num
                dados['ultimo_timestamp'] = timestamp
                dados['classe'] = melhor_det['classe']
                dados['bbox'] = melhor_det['bbox']
                dados['confianca'] = melhor_det.get('confianca', dados.get('confianca', 0))

                # Atualizar movimento
                dados['movimento'] = self._calcular_movimento(dados['centros'])
                dados['tempo_parado'] = self._calcular_tempo_parado(dados)

                veiculos_atuais.append(veiculo_id)
                detecoes_associadas.add(melhor_idx)

        # ============================
        # CRIAR NOVOS VEÍCULOS
        # ============================
        for idx, det in enumerate(detecoes):
            if idx not in detecoes_associadas:
                novo_id = self.proximo_id
                self.proximo_id += 1

                self.veiculos[novo_id] = {
                    'centros': deque([det['centro']], maxlen=self.max_historico),
                    'ultimo_centro': det['centro'],
                    'ultimo_frame': frame_num,
                    'ultimo_timestamp': timestamp,
                    'primeiro_frame': frame_num,
                    'primeiro_timestamp': timestamp,
                    'classe': det['classe'],
                    'bbox': det['bbox'],
                    'movimento': 0,
                    'tempo_parado': 0,
                    'alerta_enviado': False,
                    'confianca': det.get('confianca', 0)
                }

                self.cores[novo_id] = (
                    np.random.randint(50, 255),
                    np.random.randint(50, 255),
                    np.random.randint(50, 255)
                )

                veiculos_atuais.append(novo_id)

        # ============================
        # REMOVER VEÍCULOS ANTIGOS
        # ============================
        ids_remover = []
        for veiculo_id, dados in self.veiculos.items():
            if frame_num - dados['ultimo_frame'] > self.frames_perdidos_max:
                ids_remover.append(veiculo_id)

        for vid in ids_remover:
            del self.veiculos[vid]
            if vid in self.cores:
                del self.cores[vid]

        return veiculos_atuais

    def _calcular_movimento(self, centros):
        """
        Calcula movimento médio recente
        """
        if len(centros) < 3:
            return 0

        movimentos = []

        for i in range(1, min(10, len(centros))):
            x1, y1 = centros[-i - 1]
            x2, y2 = centros[-i]

            dist = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            movimentos.append(dist)

        if movimentos:
            return sum(movimentos) / len(movimentos)

        return 0

    def _calcular_tempo_parado(self, dados):
        """
        Calcula tempo parado
        """
        if len(dados['centros']) < 5:
            return 0

        centros = list(dados['centros'])
        frames_parado = 0

        for i in range(1, min(30, len(centros))):
            x1, y1 = centros[-i - 1]
            x2, y2 = centros[-i]

            dist = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

            if dist < self.distancia_min_movimento:
                frames_parado += 1
            else:
                break

        tempo_parado = frames_parado / self.fps
        return tempo_parado

    def get_veiculos_parados(self):
        """
        Retorna veículos parados
        """
        parados = []
        for veiculo_id, dados in self.veiculos.items():
            if dados['tempo_parado'] >= self.tempo_min_parado:
                parados.append(veiculo_id)
        return parados

    def get_dados_veiculo(self, veiculo_id):
        return self.veiculos.get(veiculo_id)


# ============================================
# PARTE 2: DETETOR DE ZONAS PROIBIDAS
# ============================================

class ZonasProibidas:
    """
    Define e verifica zonas onde estacionamento é proibido
    """
    def __init__(self, frame_shape):
        self.altura, self.largura = frame_shape[:2]
        self.zonas = []
        
    def adicionar_zona_poligono(self, pontos, nome="Zona Proibida"):
        """Adiciona uma zona poligonal"""
        self.zonas.append({
            'pontos': np.array(pontos, dtype=np.int32),
            'nome': nome,
            'cor': (0, 0, 255),
            'tipo': 'poligono'
        })
        
    def adicionar_zona_retangular(self, x1, y1, x2, y2, nome="Zona Proibida"):
        """Adiciona uma zona retangular"""
        pontos = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
        self.adicionar_zona_poligono(pontos, nome)
    
    def veiculo_em_zona_proibida(self, centro):
        """Verifica se o veículo está em alguma zona proibida"""
        for zona in self.zonas:
            resultado = cv2.pointPolygonTest(zona['pontos'], centro, False)
            if resultado >= 0:
                return True, zona['nome']
        return False, None
    
    def desenhar_zonas(self, frame):
        """Desenha as zonas proibidas no frame"""
        frame_anotado = frame.copy()
        
        for zona in self.zonas:
            cv2.polylines(frame_anotado, [zona['pontos']], True, zona['cor'], 2)
            
            # Adicionar semi-transparência
            overlay = frame_anotado.copy()
            cv2.fillPoly(overlay, [zona['pontos']], zona['cor'])
            cv2.addWeighted(overlay, 0.2, frame_anotado, 0.8, 0, frame_anotado)
            
            # Calcular centro do polígono para texto
            M = cv2.moments(zona['pontos'])
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                cv2.putText(frame_anotado, zona['nome'], 
                           (cx-50, cy-10), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.5, zona['cor'], 2)
        
        return frame_anotado


# ============================================
# PARTE 3: PROCESSAMENTO PRINCIPAL
# ============================================

def processar_video_parados(caminho_video,denuncia,salvar_video=True,tempo_min_parado=10):
    """
    Processa vídeo detetando veículos parados
    """
    print("\n" + "="*60)
    print("  DETEÇÃO DE VEÍCULOS PARADOS")

    print("="*60)

    # Carregar modelo
    modelo = YOLO('yolov8n.pt')

    if caminho_video and not os.path.isabs(caminho_video):
        caminho_video = os.path.join(settings.MEDIA_ROOT, caminho_video)

    # Abrir vídeo
    if caminho_video:
        cap = cv2.VideoCapture(caminho_video)
        print(f" Vídeo: {caminho_video}")
    else:
        cap = cv2.VideoCapture(0)
        print(" Webcam")
    
    if not cap.isOpened():
        print(" Erro ao abrir vídeo!")
        return
    
    # Obter FPS do vídeo
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30
    
    print(f" FPS do vídeo: {fps:.1f}")


    largura = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    altura = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    output_dir = os.path.join(settings.MEDIA_ROOT, "videos_processados")
    os.makedirs(output_dir, exist_ok=True)

    timestamp_nome = datetime.now().strftime('%Y%m%d_%H%M%S')
    nome_base = os.path.splitext(os.path.basename(caminho_video))[0]
    output_path = f"{output_dir}/{nome_base}_analise_parado_{timestamp_nome}.mp4"

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (largura, altura))

    # Inicializar rastreador
    rastreador = RastreadorParados(max_historico=100, fps=fps)
    rastreador.tempo_min_parado = tempo_min_parado

    #  CORREÇÃO: Ler primeiro frame corretamente
    ret, primeiro_frame = cap.read()

    if ret and primeiro_frame is not None:
        zonas = ZonasProibidas(primeiro_frame.shape)
        # Voltar ao início
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    else:
        print(" Não foi possível ler o primeiro frame!")
        return

    # Nota: deteção limitada a "veículo parado em qualquer lugar" (sem zonas
    # proibidas) — a definição interativa de zonas com o rato não é possível
    # num processo em background (worker Celery, sem ecrã nem input do utilizador).

    # Configurações
    frame_count = 0
    start_time = time.time()

    # Log
    log_path = f"{output_dir}/veiculos_parados_log_{timestamp_nome}.csv"
    log_file = open(log_path, "w")
    log_file.write("timestamp,frame,id,x,y,classe,tempo_parado,em_zona_proibida\n")

    # Alertas já enviados
    alertas_enviados = set()
    confiancas_alertas = []

    print("\n PROCESSANDO (modo automático, sem interface gráfica)...")
    print("-"*50)

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Reduzir resolução para melhor performance
        frame_pequeno = cv2.resize(frame, (640, 360))
        escala_x = frame.shape[1] / 640
        escala_y = frame.shape[0] / 360
        
        # Detetar veículos
        try:
            resultados = modelo(frame_pequeno, classes=[2, 3, 5, 7])
        except Exception as e:
            print(f"⚠️ Erro ao processar frame {frame_count}, a saltar: {e}")
            resultados = None

        # Extrair deteções
        detecoes = []
        if resultados and len(resultados) > 0:
            for det in resultados[0]:
                confianca = float(det.boxes.conf[0].cpu().numpy())

                if confianca < 0.4:
                    continue

                x1, y1, x2, y2 = det.boxes.xyxy[0].cpu().numpy().astype(int)
                classe_id = int(det.boxes.cls[0].cpu().numpy())

                # Escalar de volta
                x1 = int(x1 * escala_x)
                y1 = int(y1 * escala_y)
                x2 = int(x2 * escala_x)
                y2 = int(y2 * escala_y)

                centro_x = (x1 + x2) // 2
                centro_y = (y1 + y2) // 2

                nome_classes = {2: 'carro', 3: 'moto', 5: 'autocarro', 7: 'camiao'}
                classe = nome_classes.get(classe_id, 'desconhecido')

                detecoes.append({
                    'centro': (centro_x, centro_y),
                    'bbox': (x1, y1, x2, y2),
                    'classe': classe,
                    'confianca': confianca
                })
        
        # Atualizar tracking
        veiculos_ativos = rastreador.atualizar(detecoes, frame_count, time.time())
        
        # Desenhar
        frame_anotado = frame.copy()
        
        # Desenhar zonas proibidas
        if len(zonas.zonas) > 0:
            frame_anotado = zonas.desenhar_zonas(frame_anotado)
        
        # Processar veículos
        veiculos_parados_frame = []
        veiculos_em_zona = []
        
        for veiculo_id in veiculos_ativos:
            dados = rastreador.get_dados_veiculo(veiculo_id)
            if not dados:
                continue
            
            cor = rastreador.cores[veiculo_id]
            ultimo_centro = dados['ultimo_centro']
            x1, y1, x2, y2 = dados['bbox']
            
            # Verificar se está parado
            tempo_parado = dados['tempo_parado']
            esta_parado = tempo_parado >= rastreador.tempo_min_parado
            
            if esta_parado:
                veiculos_parados_frame.append(veiculo_id)
            
            # Verificar se está em zona proibida
            em_zona, nome_zona = zonas.veiculo_em_zona_proibida(ultimo_centro)
            if em_zona:
                veiculos_em_zona.append(veiculo_id)
            
            # Guardar log
            log_file.write(f"{timestamp},{frame_count},{veiculo_id},"
                          f"{ultimo_centro[0]},{ultimo_centro[1]},{dados['classe']},"
                          f"{tempo_parado:.1f},{1 if em_zona else 0}\n")
            
            # ALERTA: Veículo parado tempo suficiente (zona proibida é agravante,
            # não requisito — sem zonas configuráveis em modo headless, exigir
            # em_zona faria com que este alerta nunca disparasse)
            if esta_parado and veiculo_id not in alertas_enviados:
                alertas_enviados.add(veiculo_id)
                confiancas_alertas.append(dados.get('confianca', 0))
                print(f"\n  ALERTA! Veículo {veiculo_id} parado" + (f" em {nome_zona}" if em_zona else ""))
                print(f"   Tempo parado: {tempo_parado:.1f} segundos")
                print(f"   Posição: {ultimo_centro}")

                # Guardar screenshot do alerta
                screenshot_path = f"{output_dir}/alerta_parado_{veiculo_id}_{frame_count}.jpg"
                cv2.imwrite(screenshot_path, frame)
                print(f"    Screenshot: {screenshot_path}")
            
            # Desenhar bounding box
            if esta_parado:
                if em_zona:
                    # VERMELHO para parado em zona proibida
                    cv2.rectangle(frame_anotado, (x1, y1), (x2, y2), (0, 0, 255), 3)
                else:
                    # LARANJA para parado (mas não em zona proibida)
                    cv2.rectangle(frame_anotado, (x1, y1), (x2, y2), (0, 165, 255), 3)
            else:
                # COR NORMAL para em movimento
                cv2.rectangle(frame_anotado, (x1, y1), (x2, y2), cor, 2)
            
            # Desenhar ID
            cv2.putText(frame_anotado, f"ID:{veiculo_id}", (x1, y1-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, cor, 2)
            
            # Mostrar tempo parado
            if tempo_parado > 0:
                texto_tempo = f"Parado: {tempo_parado:.1f}s"
                cor_tempo = (0, 0, 255) if tempo_parado >= rastreador.tempo_min_parado else (0, 165, 255)
                cv2.putText(frame_anotado, texto_tempo, (x1, y2+20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, cor_tempo, 1)
            
            # Desenhar centro
            cv2.circle(frame_anotado, ultimo_centro, 4, (0, 0, 255), -1)
            
            # Mostrar estado
            if esta_parado:
                if em_zona:
                    cv2.putText(frame_anotado, " PARADO EM ZONA PROIBIDA!", (x1, y2+45),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                else:
                    cv2.putText(frame_anotado, "⏸ PARADO", (x1, y2+45),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)
        
        # Informações no ecrã
        fps_atual = frame_count / (time.time() - start_time)
        
        cv2.putText(frame_anotado, f"Frame: {frame_count}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame_anotado, f"Veiculos: {len(veiculos_ativos)}", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame_anotado, f"Parados: {len(veiculos_parados_frame)}", (10, 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
        cv2.putText(frame_anotado, f"Em zona proibida: {len(veiculos_em_zona)}", (10, 120),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.putText(frame_anotado, f"FPS: {fps_atual:.1f}", (10, 150),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # Tempo limite
        cv2.putText(frame_anotado, f"Limite parado: {rastreador.tempo_min_parado}s", 
                   (frame.shape[1]-200, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                   0.5, (255, 255, 0), 1)
        
        # GUARDAR FRAME NO VÍDEO
        if salvar_video and out is not None:
            out.write(frame_anotado)

    # Fechar recursos
    cap.release()
    if salvar_video:
        out.release()
    log_file.close()

    video_browser = converter_video_para_browser(output_path) if salvar_video else None

    print(f"\n Processamento concluído!")
    print(f" Log: {log_path}")
    print(f" Total frames: {frame_count}")
    print(f" Veículos únicos: {rastreador.proximo_id}")
    alertas=len(alertas_enviados)
    confianca_final = round(sum(confiancas_alertas) / len(confiancas_alertas), 2) if confiancas_alertas else 0.5

    analise = ResultadoAnaliseService.executar_analise(denuncia, video_browser or output_path, alertas, confianca_final)

    return analise




# ============================================
# PARTE 5: FUNÇÃO PRINCIPAL
# ============================================

def main_parado(path,denuncia):
    """
    Função principal com menu
    """
        
    analise = processar_video_parados(path,denuncia, salvar_video=True)
    return analise
        
        
        
      










