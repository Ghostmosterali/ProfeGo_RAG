"""
Generador de planes de estudio usando RAG + Gemini AI
Combina documentos recuperados con el prompt de Gemini
CON SOPORTE PARA ACTIVIDADES DIDÁCTICAS
"""

import logging
from typing import Dict, Optional
from gemini_service import plan_generator
import json
import time
from .metrics import get_metrics_instance

logger = logging.getLogger(__name__)

class RAGPlanGenerator:
    """
    Genera planes de estudio usando RAG
    Combina contexto recuperado con Gemini AI
    """
    
    def __init__(self):
        """Inicializa el generador RAG"""
        self.plan_generator = plan_generator
        logger.info("✅ RAGPlanGenerator inicializado")
    
    async def generate_plan_with_rag(
        self,
        plan_text: str,
        diagnostico_text: Optional[str],
        retrieved_documents: Dict
    ) -> Dict:
        """
        Genera un plan de estudios usando RAG
        
        Args:
            plan_text: Texto del plan de estudios
            diagnostico_text: Texto del diagnóstico (opcional)
            retrieved_documents: Documentos recuperados del vector store
            
        Returns:
            Plan generado con RAG
        """
        logger.info("🤖 Generando plan con RAG + Gemini AI")
        
        # Construir contexto RAG
        rag_context = self._build_rag_context(retrieved_documents)
        
        # Enriquecer el plan_text con contexto RAG
        enriched_plan_text = self._enrich_plan_with_rag(plan_text, rag_context)
        
        # Generar plan con Gemini usando el contexto enriquecido
        result = await self.plan_generator.generar_plan(
            plan_text=enriched_plan_text,
            diagnostico_text=diagnostico_text
        )
        
        if result['success']:
            # Agregar metadata RAG
            result['plan']['rag_metadata'] = {
                'cuentos_usados': len(retrieved_documents.get('cuentos', [])),
                'canciones_usadas': len(retrieved_documents.get('canciones', [])),
                'actividades_usadas': len(retrieved_documents.get('actividades', [])),
                'fuentes_rag': self._extract_sources(retrieved_documents)
            }
            
            logger.info("✅ Plan generado con RAG exitosamente")
        
        return result
    
    def _build_rag_context(self, retrieved_documents: Dict) -> str:
        """
        Construye contexto RAG a partir de documentos recuperados
        
        Args:
            retrieved_documents: Documentos recuperados
            
        Returns:
            Contexto formateado
        """
        context_parts = []
        
        # Agregar cuentos
        if retrieved_documents.get('cuentos'):
            context_parts.append("## 📖 CUENTOS RECOMENDADOS DISPONIBLES:")
            for idx, doc in enumerate(retrieved_documents['cuentos'][:5], 1):
                filename = doc['metadata'].get('filename', 'Cuento desconocido')
                text_preview = doc['text'][:300] + "..." if len(doc['text']) > 300 else doc['text']
                context_parts.append(f"\n**Cuento {idx}: {filename}**")
                context_parts.append(f"Relevancia: {doc['similarity']:.2%}")
                context_parts.append(f"Contenido: {text_preview}")
        
        # Agregar canciones
        if retrieved_documents.get('canciones'):
            context_parts.append("\n\n## 🎵 CANCIONES DIDÁCTICAS DISPONIBLES:")
            for idx, doc in enumerate(retrieved_documents['canciones'][:5], 1):
                filename = doc['metadata'].get('filename', 'Canción desconocida')
                text_preview = doc['text'][:300] + "..." if len(doc['text']) > 300 else doc['text']
                context_parts.append(f"\n**Canción {idx}: {filename}**")
                context_parts.append(f"Relevancia: {doc['similarity']:.2%}")
                context_parts.append(f"Contenido: {text_preview}")
        
        # Agregar actividades
        if retrieved_documents.get('actividades'):
            context_parts.append("\n\n## 🎯 ACTIVIDADES DIDÁCTICAS DISPONIBLES:")
            for idx, doc in enumerate(retrieved_documents['actividades'][:5], 1):
                filename = doc['metadata'].get('filename', 'Actividad desconocida')
                # Para actividades mostramos más contenido porque tienen estructura
                text_preview = doc['text'][:800] + "..." if len(doc['text']) > 800 else doc['text']
                context_parts.append(f"\n**Actividad {idx}: {filename}**")
                context_parts.append(f"Relevancia: {doc['similarity']:.2%}")
                context_parts.append(f"Contenido completo:\n{text_preview}")
        
        return "\n".join(context_parts)
    
    def _enrich_plan_with_rag(self, plan_text: str, rag_context: str) -> str:
        """
        Enriquece el plan de estudios con contexto RAG
        
        Args:
            plan_text: Texto original del plan
            rag_context: Contexto RAG construido
            
        Returns:
            Plan enriquecido
        """
        enriched = f"""
{plan_text}

---

# CONTEXTO ADICIONAL DE LA BIBLIOTECA DIGITAL

{rag_context}

---

INSTRUCCIÓN ESPECIAL: Utiliza los cuentos, canciones y actividades anteriores como INSPIRACIÓN y REFERENCIA para:
1. Recomendar recursos reales que están disponibles en la biblioteca
2. Crear actividades basadas en estos materiales
3. Sugerir variaciones usando estos recursos
4. Integrar las actividades didácticas de la biblioteca en los módulos cuando sean relevantes

IMPORTANTE SOBRE ACTIVIDADES: 
- Si una actividad de la biblioteca es perfecta para un módulo → inclúyela completa o adaptada
- Marca claramente cuando una actividad proviene de la biblioteca con "basada_en_actividad_biblioteca": "SI"
- Especifica el nombre del archivo fuente en "fuente_actividad"
- Las actividades de la biblioteca tienen estructura completa: título, ámbito, organización, materiales, desarrollo, sugerencias

IMPORTANTE SOBRE TODOS LOS RECURSOS:
- Al recomendar cuentos/canciones/actividades, PRIORIZA los que aparecen arriba
- Menciona específicamente los títulos de los recursos disponibles
- Si un recurso es muy relevante, intégralo directamente en las actividades
- Usa los recursos de la biblioteca como base para las recomendaciones de "recursos_educativos"
- Para actividades, inclúyelas en "actividades_complementarias" con todos sus detalles
"""
        
        return enriched
    
    def _extract_sources(self, retrieved_documents: Dict) -> list:
        """
        Extrae fuentes de los documentos recuperados
        
        Args:
            retrieved_documents: Documentos recuperados
            
        Returns:
            Lista de fuentes
        """
        sources = []
        
        for doc_type in ['cuentos', 'canciones', 'actividades']:
            if retrieved_documents.get(doc_type):
                for doc in retrieved_documents[doc_type]:
                    filename = doc['metadata'].get('filename', '')
                    if filename:
                        sources.append({
                            'tipo': doc_type[:-1] if doc_type.endswith('s') else doc_type,
                            'nombre': filename,
                            'similitud': round(doc['similarity'], 3)
                        })
        
        return sources