"""
Sistema RAG para ProfeGo
Inicializa todos los componentes del sistema
VERSIÓN MEJORADA CON SOPORTE PARA ACTIVIDADES
"""

import logging
import os
from pathlib import Path
from typing import Optional

from .embeddings import GeminiEmbeddings
from .vector_store import VectorStore
from .document_processor import DocumentProcessor
from .retriever import RAGRetriever
from .generator import RAGPlanGenerator

logger = logging.getLogger(__name__)

class RAGSystem:
    """
    Sistema RAG completo para ProfeGo
    Gestiona todo el pipeline: embeddings, vectorización, recuperación y generación
    """
    
    def __init__(
        self,
        vector_db_path: str = "./rag_data/vector_db",
        cuentos_dir: str = "./rag_data/cuentos",
        canciones_dir: str = "./rag_data/canciones",
        actividades_dir: str = "./rag_data/actividades"
    ):
        """
        Inicializa el sistema RAG completo
        
        Args:
            vector_db_path: Ruta a la base de datos vectorial
            cuentos_dir: Directorio con cuentos generales
            canciones_dir: Directorio con canciones generales
            actividades_dir: Directorio con actividades didácticas
        """
        logger.info("Inicializando Sistema RAG para ProfeGo...")
        
        # Crear directorios si no existen
        try:
            for directory in [vector_db_path, cuentos_dir, canciones_dir, actividades_dir]:
                dir_path = Path(directory)
                if not dir_path.exists():
                    dir_path.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Directorio creado: {directory}")
                else:
                    logger.info(f"Directorio existente: {directory}")
        except Exception as e:
            logger.warning(f"Advertencia creando directorios: {e}")
        
        # Inicializar componentes
        try:
            self.embeddings = GeminiEmbeddings()
            self.vector_store = VectorStore(persist_directory=vector_db_path)
            self.document_processor = DocumentProcessor(
                chunk_size=1000,
                chunk_overlap=200
            )
            self.retriever = RAGRetriever(
                embeddings=self.embeddings,
                vector_store=self.vector_store
            )
            self.generator = RAGPlanGenerator()
            
            # Directorios
            self.cuentos_dir = cuentos_dir
            self.canciones_dir = canciones_dir
            self.actividades_dir = actividades_dir
            
            logger.info("Sistema RAG inicializado correctamente")
        except Exception as e:
            logger.error(f"Error inicializando componentes RAG: {e}")
            raise
    
    def initialize_general_library(self) -> bool:
        """
        Inicializa la biblioteca general (cuentos, canciones y actividades)
        VERSIÓN OPTIMIZADA PARA MEMORIA
        """
        logger.info("Inicializando biblioteca general...")
        
        try:
            import gc
            total_chunks = 0
            
            # Procesar cuentos
            logger.info(f"Procesando cuentos desde {self.cuentos_dir}")
            
            try:
                cuentos_chunks = self.document_processor.process_directory(
                    self.cuentos_dir,
                    document_type='cuento',
                    recursive=True
                )
                
                if cuentos_chunks:
                    batch_size = 3
                    logger.info(f"Generando embeddings para {len(cuentos_chunks)} chunks de cuentos...")
                    
                    for i in range(0, len(cuentos_chunks), batch_size):
                        batch = cuentos_chunks[i:i+batch_size]
                        logger.info(f"Procesando lote {i//batch_size + 1}/{(len(cuentos_chunks) + batch_size - 1)//batch_size}")
                        
                        batch_embeddings = self.embeddings.embed_documents(
                            [chunk['text'] for chunk in batch]
                        )
                        
                        self.vector_store.add_documents(batch, batch_embeddings)
                        total_chunks += len(batch)
                        
                        del batch_embeddings
                        gc.collect()
                    
                    logger.info(f"{len(cuentos_chunks)} chunks de cuentos indexados")
                else:
                    logger.info("No se encontraron chunks de cuentos")
            except Exception as e:
                logger.error(f"Error procesando cuentos: {type(e).__name__}: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Procesar canciones
            logger.info(f"Procesando canciones desde {self.canciones_dir}")
            
            try:
                canciones_chunks = self.document_processor.process_directory(
                    self.canciones_dir,
                    document_type='cancion',
                    recursive=True
                )
                
                if canciones_chunks:
                    batch_size = 3
                    logger.info(f"Generando embeddings para {len(canciones_chunks)} chunks de canciones...")
                    
                    for i in range(0, len(canciones_chunks), batch_size):
                        batch = canciones_chunks[i:i+batch_size]
                        logger.info(f"Procesando lote {i//batch_size + 1}/{(len(canciones_chunks) + batch_size - 1)//batch_size}")
                        
                        batch_embeddings = self.embeddings.embed_documents(
                            [chunk['text'] for chunk in batch]
                        )
                        
                        self.vector_store.add_documents(batch, batch_embeddings)
                        total_chunks += len(batch)
                        
                        del batch_embeddings
                        gc.collect()
                    
                    logger.info(f"{len(canciones_chunks)} chunks de canciones indexados")
                else:
                    logger.info("No se encontraron chunks de canciones")
            except Exception as e:
                logger.error(f"Error procesando canciones: {type(e).__name__}: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Procesar actividades
            logger.info(f"Procesando actividades desde {self.actividades_dir}")
            
            try:
                actividades_chunks = self.document_processor.process_directory(
                    self.actividades_dir,
                    document_type='actividad',
                    recursive=True
                )
                
                if actividades_chunks:
                    batch_size = 3
                    logger.info(f"Generando embeddings para {len(actividades_chunks)} chunks de actividades...")
                    
                    for i in range(0, len(actividades_chunks), batch_size):
                        batch = actividades_chunks[i:i+batch_size]
                        logger.info(f"Procesando lote {i//batch_size + 1}/{(len(actividades_chunks) + batch_size - 1)//batch_size}")
                        
                        batch_embeddings = self.embeddings.embed_documents(
                            [chunk['text'] for chunk in batch]
                        )
                        
                        self.vector_store.add_documents(batch, batch_embeddings)
                        total_chunks += len(batch)
                        
                        del batch_embeddings
                        gc.collect()
                    
                    logger.info(f"{len(actividades_chunks)} chunks de actividades indexados")
                else:
                    logger.info("No se encontraron chunks de actividades")
            except Exception as e:
                logger.error(f"Error procesando actividades: {type(e).__name__}: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
            
            if total_chunks > 0:
                logger.info(f"Biblioteca general inicializada: {total_chunks} chunks totales")
                return True
            else:
                logger.warning("No se indexaron documentos (biblioteca vacia)")
                return False
                
        except Exception as e:
            logger.error(f"Error inicializando biblioteca general: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(f"Traceback completo: {traceback.format_exc()}")
            return False
    
    def index_user_documents(
        self,
        user_email: str,
        plan_content: bytes,
        plan_filename: str,
        diagnostico_content: Optional[bytes] = None,
        diagnostico_filename: Optional[str] = None
    ) -> bool:
        """Indexa documentos de un usuario específico"""
        logger.info(f"Indexando documentos del usuario: {user_email}")
        
        try:
            self.vector_store.delete_documents({'user_email': user_email})
            logger.info(f"Documentos antiguos del usuario eliminados")
            
            all_chunks = []
            all_embeddings = []
            
            # Procesar plan
            logger.info(f"Procesando plan: {plan_filename}")
            plan_text = self.document_processor.extract_text_from_bytes(
                plan_content,
                plan_filename
            )
            
            if plan_text:
                plan_chunks = self.document_processor.split_text_into_chunks(
                    plan_text,
                    metadata={
                        'filename': plan_filename,
                        'document_type': 'plan',
                        'user_email': user_email
                    }
                )
                
                plan_embeddings = self.embeddings.embed_documents(
                    [chunk['text'] for chunk in plan_chunks]
                )
                
                all_chunks.extend(plan_chunks)
                all_embeddings.extend(plan_embeddings)
                
                logger.info(f"Plan procesado: {len(plan_chunks)} chunks")
            
            # Procesar diagnóstico si existe
            if diagnostico_content and diagnostico_filename:
                logger.info(f"Procesando diagnostico: {diagnostico_filename}")
                diagnostico_text = self.document_processor.extract_text_from_bytes(
                    diagnostico_content,
                    diagnostico_filename
                )
                
                if diagnostico_text:
                    diag_chunks = self.document_processor.split_text_into_chunks(
                        diagnostico_text,
                        metadata={
                            'filename': diagnostico_filename,
                            'document_type': 'diagnostico',
                            'user_email': user_email
                        }
                    )
                    
                    diag_embeddings = self.embeddings.embed_documents(
                        [chunk['text'] for chunk in diag_chunks]
                    )
                    
                    all_chunks.extend(diag_chunks)
                    all_embeddings.extend(diag_embeddings)
                    
                    logger.info(f"Diagnostico procesado: {len(diag_chunks)} chunks")
            
            if all_chunks:
                self.vector_store.add_documents(all_chunks, all_embeddings)
                logger.info(f"Documentos del usuario indexados: {len(all_chunks)} chunks totales")
                return True
            else:
                logger.warning("No se generaron chunks para indexar")
                return False
            
        except Exception as e:
            logger.error(f"Error indexando documentos del usuario: {e}")
            return False
    
    async def generate_plan_with_rag(
        self,
        user_email: str,
        plan_text: str,
        diagnostico_text: Optional[str] = None
    ):
        """Genera un plan de estudios usando RAG"""
        logger.info(f"Generando plan con RAG para usuario: {user_email}")
        
        try:
            retrieved_docs = self.retriever.retrieve_for_plan_generation(
                plan_text=plan_text,
                diagnostico_text=diagnostico_text,
                user_email=user_email,
                n_results=15
            )
            
            result = await self.generator.generate_plan_with_rag(
                plan_text=plan_text,
                diagnostico_text=diagnostico_text,
                retrieved_documents=retrieved_docs
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error generando plan con RAG: {e}")
            return {
                'success': False,
                'error': f'Error generando plan con RAG: {str(e)}'
            }
    
    def get_stats(self) -> dict:
        """Obtiene estadísticas del sistema RAG"""
        return self.vector_store.get_collection_stats()
    
    def reset_system(self) -> bool:
        """Reinicia todo el sistema RAG"""
        logger.warning("Reiniciando sistema RAG...")
        return self.vector_store.reset_collection()


# Instancia global del sistema RAG
rag_system: Optional[RAGSystem] = None


def initialize_rag_system():
    """Inicializa el sistema RAG global"""
    global rag_system
    
    if rag_system is None:
        try:
            rag_system = RAGSystem()
            logger.info("Sistema RAG global inicializado")
        except Exception as e:
            logger.error(f"Error inicializando RAG system: {e}")
            rag_system = None
    
    return rag_system


def get_rag_system() -> RAGSystem:
    """Obtiene la instancia del sistema RAG"""
    if rag_system is None:
        return initialize_rag_system()
    
    return rag_system