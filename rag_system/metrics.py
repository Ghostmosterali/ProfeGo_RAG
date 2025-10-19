"""
Sistema de métricas y logging para demostrar el uso de RAG
Registra todas las operaciones RAG para auditoría y análisis
"""

import logging
import json
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class RAGMetrics:
    """
    Registra y almacena métricas del sistema RAG
    Permite demostrar que RAG está funcionando correctamente
    """
    
    def __init__(self, log_file: str = "./rag_data/rag_metrics.json"):
        """
        Inicializa el sistema de métricas
        
        Args:
            log_file: Archivo donde se guardan las métricas
        """
        self.log_file = log_file
        self.current_session = {
            'session_id': None,
            'user_email': None,
            'timestamp_start': None,
            'timestamp_end': None,
            'indexing_metrics': {},
            'retrieval_metrics': {},
            'generation_metrics': {},
            'rag_impact': {}
        }
        
        # Crear directorio si no existe
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    
    def start_session(self, user_email: str, plan_filename: str) -> str:
        """
        Inicia una nueva sesión de generación con RAG
        
        Args:
            user_email: Email del usuario
            plan_filename: Nombre del archivo del plan
            
        Returns:
            ID de la sesión
        """
        session_id = f"{user_email}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.current_session = {
            'session_id': session_id,
            'user_email': user_email,
            'plan_filename': plan_filename,
            'timestamp_start': datetime.now().isoformat(),
            'timestamp_end': None,
            'indexing_metrics': {},
            'retrieval_metrics': {},
            'generation_metrics': {},
            'rag_impact': {}
        }
        
        logger.info(f"📊 Sesión RAG iniciada: {session_id}")
        return session_id
    
    def log_indexing(
        self,
        plan_chunks: int,
        diagnostico_chunks: int,
        total_embeddings: int,
        indexing_time: float
    ):
        """
        Registra métricas de indexación
        
        Args:
            plan_chunks: Número de chunks del plan
            diagnostico_chunks: Número de chunks del diagnóstico
            total_embeddings: Total de embeddings generados
            indexing_time: Tiempo de indexación en segundos
        """
        self.current_session['indexing_metrics'] = {
            'plan_chunks': plan_chunks,
            'diagnostico_chunks': diagnostico_chunks,
            'total_chunks': plan_chunks + diagnostico_chunks,
            'total_embeddings': total_embeddings,
            'indexing_time_seconds': round(indexing_time, 2),
            'embeddings_per_second': round(total_embeddings / indexing_time, 2) if indexing_time > 0 else 0
        }
        
        logger.info(f"📝 Indexación completada: {total_embeddings} embeddings en {indexing_time:.2f}s")
    
    def log_retrieval(
        self,
        cuentos_retrieved: List[Dict],
        canciones_retrieved: List[Dict],
        retrieval_time: float
    ):
        """
        Registra métricas de recuperación
        
        Args:
            cuentos_retrieved: Lista de cuentos recuperados
            canciones_retrieved: Lista de canciones recuperadas
            retrieval_time: Tiempo de recuperación
        """
        # Calcular similitud promedio
        avg_cuento_similarity = sum(c['similarity'] for c in cuentos_retrieved) / len(cuentos_retrieved) if cuentos_retrieved else 0
        avg_cancion_similarity = sum(c['similarity'] for c in canciones_retrieved) / len(canciones_retrieved) if canciones_retrieved else 0
        
        self.current_session['retrieval_metrics'] = {
            'cuentos_count': len(cuentos_retrieved),
            'canciones_count': len(canciones_retrieved),
            'total_retrieved': len(cuentos_retrieved) + len(canciones_retrieved),
            'avg_cuento_similarity': round(avg_cuento_similarity, 3),
            'avg_cancion_similarity': round(avg_cancion_similarity, 3),
            'retrieval_time_seconds': round(retrieval_time, 2),
            'cuentos_details': [
                {
                    'filename': c['metadata'].get('filename', 'unknown'),
                    'similarity': round(c['similarity'], 3),
                    'preview': c['text'][:100] + '...'
                }
                for c in cuentos_retrieved[:3]  # Solo los 3 más relevantes
            ],
            'canciones_details': [
                {
                    'filename': c['metadata'].get('filename', 'unknown'),
                    'similarity': round(c['similarity'], 3),
                    'preview': c['text'][:100] + '...'
                }
                for c in canciones_retrieved[:3]
            ]
        }
        
        logger.info(f"🔍 Recuperación: {len(cuentos_retrieved)} cuentos, {len(canciones_retrieved)} canciones")
    
    def log_generation(
        self,
        plan_generated: Dict,
        generation_time: float,
        rag_context_size: int
    ):
        """
        Registra métricas de generación
        
        Args:
            plan_generated: Plan generado
            generation_time: Tiempo de generación
            rag_context_size: Tamaño del contexto RAG en caracteres
        """
        self.current_session['generation_metrics'] = {
            'plan_name': plan_generated.get('nombre_plan', 'N/A'),
            'num_modulos': plan_generated.get('num_modulos', 0),
            'generation_time_seconds': round(generation_time, 2),
            'rag_context_size_chars': rag_context_size,
            'rag_metadata': plan_generated.get('rag_metadata', {})
        }
        
        logger.info(f"🤖 Plan generado: {plan_generated.get('nombre_plan')} con {rag_context_size} caracteres de contexto RAG")
    
    def analyze_rag_impact(self, plan_generated: Dict, retrieved_docs: Dict):
        """
        Analiza el impacto real del RAG en el plan generado
        ESTO ES LA CLAVE PARA JUSTIFICAR QUE RAG FUNCIONA
        
        Args:
            plan_generated: Plan generado
            retrieved_docs: Documentos recuperados
        """
        impact = {
            'recursos_rag_utilizados': 0,
            'recursos_rag_mencionados': [],
            'actividades_basadas_rag': 0,
            'evidencias_rag': []
        }
        
        # Extraer nombres de archivos recuperados
        recursos_disponibles = []
        for cuento in retrieved_docs.get('cuentos', []):
            filename = cuento['metadata'].get('filename', '')
            if filename:
                recursos_disponibles.append(filename.lower())
        
        for cancion in retrieved_docs.get('canciones', []):
            filename = cancion['metadata'].get('filename', '')
            if filename:
                recursos_disponibles.append(filename.lower())
        
        # Analizar el plan generado
        plan_text = json.dumps(plan_generated, ensure_ascii=False).lower()
        
        # Buscar menciones de recursos RAG
        for recurso in recursos_disponibles:
            recurso_base = Path(recurso).stem.lower()
            if recurso_base in plan_text:
                impact['recursos_rag_utilizados'] += 1
                impact['recursos_rag_mencionados'].append(recurso)
                impact['evidencias_rag'].append(f"✅ Recurso '{recurso}' mencionado en el plan")
        
        # Analizar recursos educativos en el plan
        if 'recursos_educativos' in plan_generated:
            recursos_plan = plan_generated['recursos_educativos']
            
            # Cuentos recomendados
            if 'cuentos_recomendados' in recursos_plan:
                for cuento in recursos_plan['cuentos_recomendados']:
                    titulo = cuento.get('titulo', '').lower()
                    # Verificar si coincide con algún recurso RAG
                    for recurso in recursos_disponibles:
                        if Path(recurso).stem.lower() in titulo or titulo in Path(recurso).stem.lower():
                            impact['evidencias_rag'].append(f"✅ Cuento '{cuento.get('titulo')}' proviene de la biblioteca RAG")
            
            # Canciones recomendadas
            if 'canciones_recomendadas' in recursos_plan:
                for cancion in recursos_plan['canciones_recomendadas']:
                    titulo = cancion.get('titulo', '').lower()
                    for recurso in recursos_disponibles:
                        if Path(recurso).stem.lower() in titulo or titulo in Path(recurso).stem.lower():
                            impact['evidencias_rag'].append(f"✅ Canción '{cancion.get('titulo')}' proviene de la biblioteca RAG")
        
        # Analizar módulos
        actividades_rag = 0
        for modulo in plan_generated.get('modulos', []):
            # Buscar referencias a recursos RAG en actividades
            modulo_text = json.dumps(modulo, ensure_ascii=False).lower()
            for recurso in recursos_disponibles:
                if Path(recurso).stem.lower() in modulo_text:
                    actividades_rag += 1
                    break
        
        impact['actividades_basadas_rag'] = actividades_rag
        
        # Calcular porcentaje de impacto
        total_recursos_plan = 0
        if 'recursos_educativos' in plan_generated:
            total_recursos_plan += len(plan_generated['recursos_educativos'].get('cuentos_recomendados', []))
            total_recursos_plan += len(plan_generated['recursos_educativos'].get('canciones_recomendadas', []))
        
        if total_recursos_plan > 0:
            impact['porcentaje_recursos_rag'] = round((impact['recursos_rag_utilizados'] / total_recursos_plan) * 100, 1)
        else:
            impact['porcentaje_recursos_rag'] = 0
        
        self.current_session['rag_impact'] = impact
        
        logger.info(f"📈 Impacto RAG: {impact['recursos_rag_utilizados']} recursos utilizados, {impact['actividades_basadas_rag']} actividades basadas en RAG")
    
    def end_session(self):
        """Finaliza la sesión y guarda las métricas"""
        self.current_session['timestamp_end'] = datetime.now().isoformat()
        
        # Calcular tiempo total
        start = datetime.fromisoformat(self.current_session['timestamp_start'])
        end = datetime.fromisoformat(self.current_session['timestamp_end'])
        total_time = (end - start).total_seconds()
        
        self.current_session['total_time_seconds'] = round(total_time, 2)
        
        # Guardar métricas
        self._save_metrics()
        
        logger.info(f"✅ Sesión RAG finalizada: {self.current_session['session_id']}")
        
        return self.current_session
    
    def _save_metrics(self):
        """Guarda las métricas en el archivo JSON"""
        try:
            # Cargar métricas existentes
            existing_metrics = []
            if Path(self.log_file).exists():
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    existing_metrics = json.load(f)
            
            # Agregar nueva sesión
            existing_metrics.append(self.current_session)
            
            # Guardar
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(existing_metrics, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Métricas guardadas en {self.log_file}")
            
        except Exception as e:
            logger.error(f"❌ Error guardando métricas: {e}")
    
    def generate_report(self) -> Dict:
        """
        Genera un reporte visual de la sesión actual
        ESTE ES EL REPORTE QUE DEMUESTRA QUE RAG FUNCIONA
        
        Returns:
            Diccionario con el reporte formateado
        """
        metrics = self.current_session
        
        report = {
            'session_id': metrics['session_id'],
            'user_email': metrics['user_email'],
            'timestamp': metrics['timestamp_start'],
            
            'indexing_summary': f"""
📝 INDEXACIÓN
  • Plan dividido en: {metrics['indexing_metrics'].get('plan_chunks', 0)} chunks
  • Diagnóstico dividido en: {metrics['indexing_metrics'].get('diagnostico_chunks', 0)} chunks
  • Total embeddings generados: {metrics['indexing_metrics'].get('total_embeddings', 0)}
  • Tiempo: {metrics['indexing_metrics'].get('indexing_time_seconds', 0)}s
  • Velocidad: {metrics['indexing_metrics'].get('embeddings_per_second', 0)} embeddings/s
""",
            
            'retrieval_summary': f"""
🔍 RECUPERACIÓN RAG
  • Cuentos recuperados: {metrics['retrieval_metrics'].get('cuentos_count', 0)}
  • Canciones recuperadas: {metrics['retrieval_metrics'].get('canciones_count', 0)}
  • Similitud promedio (cuentos): {metrics['retrieval_metrics'].get('avg_cuento_similarity', 0):.1%}
  • Similitud promedio (canciones): {metrics['retrieval_metrics'].get('avg_cancion_similarity', 0):.1%}
  • Tiempo de búsqueda: {metrics['retrieval_metrics'].get('retrieval_time_seconds', 0)}s
""",
            
            'generation_summary': f"""
🤖 GENERACIÓN CON RAG
  • Plan generado: {metrics['generation_metrics'].get('plan_name', 'N/A')}
  • Módulos: {metrics['generation_metrics'].get('num_modulos', 0)}
  • Contexto RAG: {metrics['generation_metrics'].get('rag_context_size_chars', 0)} caracteres
  • Tiempo: {metrics['generation_metrics'].get('generation_time_seconds', 0)}s
""",
            
            'rag_impact_summary': f"""
📈 IMPACTO REAL DEL RAG
  • Recursos de biblioteca utilizados: {metrics['rag_impact'].get('recursos_rag_utilizados', 0)}
  • Actividades basadas en RAG: {metrics['rag_impact'].get('actividades_basadas_rag', 0)}
  • % de recursos del plan que vienen de RAG: {metrics['rag_impact'].get('porcentaje_recursos_rag', 0)}%
  
  EVIDENCIAS:
{chr(10).join('  ' + e for e in metrics['rag_impact'].get('evidencias_rag', []))}
""",
            
            'recursos_utilizados': metrics['retrieval_metrics'].get('cuentos_details', []) + 
                                  metrics['retrieval_metrics'].get('canciones_details', []),
            
            'rag_metadata': metrics['generation_metrics'].get('rag_metadata', {})
        }
        
        return report


# Instancia global de métricas
_metrics_instance = None

def get_metrics_instance() -> RAGMetrics:
    """Obtiene la instancia global de métricas"""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = RAGMetrics()
    return _metrics_instance
