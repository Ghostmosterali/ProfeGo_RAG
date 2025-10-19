"""
Módulo para gestión de embeddings usando Sentence Transformers
VERSIÓN LIGERA PARA SISTEMAS CON POCA RAM
"""

from sentence_transformers import SentenceTransformer
from typing import List
import logging

logger = logging.getLogger(__name__)

class GeminiEmbeddings:
    """
    Clase para generar embeddings usando Sentence Transformers
    VERSIÓN OPTIMIZADA PARA MEMORIA
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Inicializa el generador de embeddings
        
        Args:
            model_name: Nombre del modelo (por defecto: all-MiniLM-L6-v2, muy ligero)
        """
        self.model_name = model_name
        self.dimension = 384  # Dimensión del modelo MiniLM
        
        logger.info(f"Cargando modelo de embeddings: {model_name}...")
        self.model = SentenceTransformer(model_name)
        logger.info(f"Modelo cargado correctamente")
    
    def embed_text(self, text: str) -> List[float]:
        """
        Genera embedding para un texto individual
        
        Args:
            text: Texto a convertir en embedding
            
        Returns:
            Vector de embeddings
        """
        try:
            if not text or not text.strip():
                logger.warning("Texto vacio recibido para embedding")
                return [0.0] * self.dimension
            
            embedding = self.model.encode(text, show_progress_bar=False)
            return embedding.tolist()
            
        except Exception as e:
            logger.error(f"Error generando embedding: {e}")
            return [0.0] * self.dimension
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Genera embeddings para múltiples documentos
        
        Args:
            texts: Lista de textos
            
        Returns:
            Lista de vectores de embeddings
        """
        try:
            logger.info(f"Generando {len(texts)} embeddings...")
            
            # Procesar en batch (más eficiente)
            embeddings = self.model.encode(
                texts, 
                show_progress_bar=False,
                batch_size=8  # Procesar de 8 en 8
            )
            
            logger.info(f"{len(embeddings)} embeddings generados")
            return [emb.tolist() for emb in embeddings]
            
        except Exception as e:
            logger.error(f"Error generando embeddings: {e}")
            # Retornar embeddings vacíos como fallback
            return [[0.0] * self.dimension for _ in texts]
    
    def embed_query(self, query: str) -> List[float]:
        """
        Genera embedding para una consulta
        
        Args:
            query: Consulta del usuario
            
        Returns:
            Vector de embedding
        """
        return self.embed_text(query)