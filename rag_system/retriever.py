"""
Sistema de recuperación para RAG
Combina búsqueda vectorial con filtros inteligentes
"""

import logging
from typing import List, Dict, Optional
from .embeddings import GeminiEmbeddings
from .vector_store import VectorStore

logger = logging.getLogger(__name__)

class RAGRetriever:
    """
    Sistema de recuperación para RAG
    Busca documentos relevantes para generar planes personalizados
    """
    
    def __init__(
        self,
        embeddings: GeminiEmbeddings,
        vector_store: VectorStore
    ):
        """
        Inicializa el retriever
        
        Args:
            embeddings: Generador de embeddings
            vector_store: Base de datos vectorial
        """
        self.embeddings = embeddings
        self.vector_store = vector_store
        
        logger.info("✅ RAGRetriever inicializado")
    
    def retrieve_for_plan_generation(
        self,
        plan_text: str,
        diagnostico_text: Optional[str],
        user_email: str,
        n_results: int = 10
    ) -> Dict:
        """
        Recupera documentos relevantes para generar un plan de estudios
        
        Args:
            plan_text: Texto del plan de estudios
            diagnostico_text: Texto del diagnóstico (opcional)
            user_email: Email del usuario
            n_results: Número de documentos a recuperar
            
        Returns:
            Diccionario con documentos recuperados por categoría
        """
        logger.info(f"🔍 Recuperando documentos para generación de plan (usuario: {user_email})")
        
        # Combinar textos para crear query
        query_text = plan_text
        if diagnostico_text:
            query_text = f"{plan_text}\n\n{diagnostico_text}"
        
        # Generar embedding de la query
        query_embedding = self.embeddings.embed_query(query_text)
        
        # Recuperar documentos generales (cuentos y canciones)
        results = {
            'cuentos': self._retrieve_by_type(query_embedding, 'cuento', n_results // 2),
            'canciones': self._retrieve_by_type(query_embedding, 'cancion', n_results // 2),
            'diagnostico_usuario': None,
            'plan_usuario': None
        }
        
        # Recuperar documentos específicos del usuario
        user_docs = self._retrieve_user_documents(query_embedding, user_email, 5)
        
        if user_docs:
            results['diagnostico_usuario'] = user_docs.get('diagnostico')
            results['plan_usuario'] = user_docs.get('plan')
        
        # Log de resultados
        logger.info(f"📚 Recuperados: {len(results['cuentos'])} cuentos, {len(results['canciones'])} canciones")
        
        return results
    
    def _retrieve_by_type(
        self,
        query_embedding: List[float],
        document_type: str,
        n_results: int
    ) -> List[Dict]:
        """
        Recupera documentos de un tipo específico
        
        Args:
            query_embedding: Embedding de la query
            document_type: Tipo de documento (cuento, cancion, etc.)
            n_results: Número de resultados
            
        Returns:
            Lista de documentos con metadata
        """
        results = self.vector_store.query(
            query_embedding=query_embedding,
            n_results=n_results,
            filter_metadata={'document_type': document_type}
        )
        
        documents = []
        for doc, metadata, distance in zip(
            results['documents'],
            results['metadatas'],
            results['distances']
        ):
            documents.append({
                'text': doc,
                'metadata': metadata,
                'similarity': 1 - distance  # Convertir distancia a similitud
            })
        
        return documents
    
    def _retrieve_user_documents(
        self,
        query_embedding: List[float],
        user_email: str,
        n_results: int
    ) -> Optional[Dict]:
        """
        Recupera documentos específicos de un usuario
        
        Args:
            query_embedding: Embedding de la query
            user_email: Email del usuario
            n_results: Número de resultados
            
        Returns:
            Diccionario con documentos del usuario
        """
        try:
            results = self.vector_store.query(
                query_embedding=query_embedding,
                n_results=n_results,
                filter_metadata={'user_email': user_email}
            )
            
            user_docs = {
                'diagnostico': [],
                'plan': []
            }
            
            for doc, metadata, distance in zip(
                results['documents'],
                results['metadatas'],
                results['distances']
            ):
                doc_type = metadata.get('document_type', '')
                
                doc_data = {
                    'text': doc,
                    'metadata': metadata,
                    'similarity': 1 - distance
                }
                
                if doc_type == 'diagnostico':
                    user_docs['diagnostico'].append(doc_data)
                elif doc_type == 'plan':
                    user_docs['plan'].append(doc_data)
            
            return user_docs if (user_docs['diagnostico'] or user_docs['plan']) else None
            
        except Exception as e:
            logger.error(f"❌ Error recuperando documentos del usuario: {e}")
            return None