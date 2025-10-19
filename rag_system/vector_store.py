"""
Base de datos vectorial usando ChromaDB para el sistema RAG
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

class VectorStore:
    """
    Gestiona la base de datos vectorial con ChromaDB
    """
    
    def __init__(
        self,
        persist_directory: str = "./rag_data/vector_db",
        collection_name: str = "profego_documents"
    ):
        """
        Inicializa el almacén vectorial
        
        Args:
            persist_directory: Directorio para persistir la base de datos
            collection_name: Nombre de la colección
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        
        # Crear directorio si no existe
        Path(persist_directory).mkdir(parents=True, exist_ok=True)
        
        # Inicializar cliente ChromaDB
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Obtener o crear colección
        try:
            self.collection = self.client.get_collection(name=collection_name)
            logger.info(f"✅ Colección '{collection_name}' cargada")
        except:
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"✅ Colección '{collection_name}' creada")
    
    def add_documents(
        self,
        chunks: List[Dict],
        embeddings: List[List[float]]
    ) -> bool:
        """
        Agrega documentos a la base de datos vectorial
        
        Args:
            chunks: Lista de chunks con metadata
            embeddings: Lista de embeddings correspondientes
            
        Returns:
            True si se agregaron correctamente
        """
        try:
            if len(chunks) != len(embeddings):
                logger.error("❌ Número de chunks y embeddings no coincide")
                return False
            
            if not chunks:
                logger.warning("⚠️ No hay chunks para agregar")
                return False
            
            # Preparar datos
            ids = [f"{chunk.get('filename', 'doc')}_{chunk['chunk_id']}" for chunk in chunks]
            documents = [chunk['text'] for chunk in chunks]
            metadatas = [
                {
                    'filename': chunk.get('filename', ''),
                    'document_type': chunk.get('document_type', ''),
                    'chunk_id': chunk['chunk_id'],
                    'user_email': chunk.get('user_email', 'general')
                }
                for chunk in chunks
            ]
            
            # Agregar a ChromaDB
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            
            logger.info(f"✅ {len(chunks)} chunks agregados a la base de datos vectorial")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error agregando documentos: {e}")
            return False
    
    def query(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        filter_metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Busca documentos similares a la consulta
        
        Args:
            query_embedding: Embedding de la consulta
            n_results: Número de resultados a retornar
            filter_metadata: Filtros de metadata (ej: {'document_type': 'cuento'})
            
        Returns:
            Resultados de la búsqueda
        """
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=filter_metadata,
                include=['documents', 'metadatas', 'distances']
            )
            
            logger.info(f"🔍 Query ejecutado: {len(results['documents'][0])} resultados")
            
            return {
                'documents': results['documents'][0],
                'metadatas': results['metadatas'][0],
                'distances': results['distances'][0]
            }
            
        except Exception as e:
            logger.error(f"❌ Error en query: {e}")
            return {
                'documents': [],
                'metadatas': [],
                'distances': []
            }
    
    def delete_documents(self, filter_metadata: Dict) -> bool:
        """
        Elimina documentos basados en metadata
        
        Args:
            filter_metadata: Filtros (ej: {'user_email': 'user@example.com'})
            
        Returns:
            True si se eliminaron correctamente
        """
        try:
            # Obtener IDs a eliminar
            results = self.collection.get(where=filter_metadata)
            
            if results['ids']:
                self.collection.delete(ids=results['ids'])
                logger.info(f"🗑️ {len(results['ids'])} documentos eliminados")
                return True
            else:
                logger.info("ℹ️ No se encontraron documentos para eliminar")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error eliminando documentos: {e}")
            return False
    
    def get_collection_stats(self) -> Dict:
        """
        Obtiene estadísticas de la colección
        
        Returns:
            Diccionario con estadísticas
        """
        try:
            count = self.collection.count()
            
            return {
                'total_documents': count,
                'collection_name': self.collection_name,
                'persist_directory': self.persist_directory
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas: {e}")
            return {
                'total_documents': 0,
                'error': str(e)
            }
    
    def reset_collection(self) -> bool:
        """
        Reinicia la colección (elimina todos los documentos)
        
        Returns:
            True si se reinició correctamente
        """
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"🔄 Colección '{self.collection_name}' reiniciada")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error reiniciando colección: {e}")
            return False