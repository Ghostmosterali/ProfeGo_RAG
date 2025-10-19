"""
Script de prueba del sistema RAG
Prueba todos los componentes de forma independiente
"""

import asyncio
import logging
from pathlib import Path
import sys

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from rag_system import RAGSystem

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def test_embeddings():
    """Prueba el sistema de embeddings"""
    print("\n" + "="*60)
    print("🧪 TEST 1: Embeddings con Gemini")
    print("="*60)
    
    try:
        from rag_system.embeddings import GeminiEmbeddings
        
        embeddings = GeminiEmbeddings()
        
        # Probar embedding de texto
        texto_prueba = "El patito feo es un cuento infantil sobre la aceptación"
        embedding = embeddings.embed_text(texto_prueba)
        
        print(f"✅ Embedding generado")
        print(f"   Dimensión: {len(embedding)}")
        print(f"   Primeros valores: {embedding[:5]}")
        
        # Probar embedding de query
        query = "cuentos sobre animales"
        query_embedding = embeddings.embed_query(query)
        
        print(f"✅ Query embedding generado")
        print(f"   Dimensión: {len(query_embedding)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en test de embeddings: {e}")
        return False

def test_document_processor():
    """Prueba el procesador de documentos"""
    print("\n" + "="*60)
    print("🧪 TEST 2: Procesador de Documentos")
    print("="*60)
    
    try:
        from rag_system.document_processor import DocumentProcessor
        
        processor = DocumentProcessor(chunk_size=500, chunk_overlap=100)
        
        # Crear texto de prueba
        texto_largo = "Lorem ipsum dolor sit amet. " * 100
        
        chunks = processor.split_text_into_chunks(
            texto_largo,
            metadata={'test': True}
        )
        
        print(f"✅ Texto dividido en chunks")
        print(f"   Total de chunks: {len(chunks)}")
        print(f"   Tamaño promedio: {sum(len(c['text']) for c in chunks) / len(chunks):.0f} caracteres")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en test de procesador: {e}")
        return False

def test_vector_store():
    """Prueba el almacén vectorial"""
    print("\n" + "="*60)
    print("🧪 TEST 3: Vector Store (ChromaDB)")
    print("="*60)
    
    try:
        from rag_system.vector_store import VectorStore
        from rag_system.embeddings import GeminiEmbeddings
        
        # Crear vector store temporal
        vector_store = VectorStore(
            persist_directory="./test_vector_db",
            collection_name="test_collection"
        )
        
        embeddings = GeminiEmbeddings()
        
        # Crear documentos de prueba
        chunks = [
            {
                'text': 'El patito feo es un cuento sobre la aceptación',
                'filename': 'patito.txt',
                'document_type': 'cuento',
                'chunk_id': 0,
                'user_email': 'test@test.com'
            },
            {
                'text': 'La tortuga y la liebre corrieron una carrera',
                'filename': 'tortuga.txt',
                'document_type': 'cuento',
                'chunk_id': 0,
                'user_email': 'test@test.com'
            }
        ]
        
        # Generar embeddings
        texts = [c['text'] for c in chunks]
        chunk_embeddings = embeddings.embed_documents(texts)
        
        # Agregar a vector store
        vector_store.add_documents(chunks, chunk_embeddings)
        
        print(f"✅ Documentos agregados al vector store")
        
        # Probar búsqueda
        query = "cuentos sobre animales"
        query_embedding = embeddings.embed_query(query)
        
        results = vector_store.query(
            query_embedding=query_embedding,
            n_results=2
        )
        
        print(f"✅ Búsqueda ejecutada")
        print(f"   Resultados: {len(results['documents'])}")
        for i, doc in enumerate(results['documents']):
            print(f"   {i+1}. {doc[:50]}... (similitud: {1-results['distances'][i]:.3f})")
        
        # Limpiar
        vector_store.reset_collection()
        
        import shutil
        shutil.rmtree("./test_vector_db", ignore_errors=True)
        
        return True
        
    except Exception as e:
        print(f"❌ Error en test de vector store: {e}")
        return False

async def test_full_system():
    """Prueba el sistema completo"""
    print("\n" + "="*60)
    print("🧪 TEST 4: Sistema RAG Completo")
    print("="*60)
    
    try:
        # Crear sistema RAG temporal
        rag = RAGSystem(
            vector_db_path="./test_rag_db",
            cuentos_dir="./rag_data/cuentos",
            canciones_dir="./rag_data/canciones"
        )
        
        print("✅ Sistema RAG inicializado")
        
        # Obtener estadísticas
        stats = rag.get_stats()
        print(f"✅ Estadísticas obtenidas")
        print(f"   Total documentos: {stats['total_documents']}")
        
        # Limpiar
        import shutil
        shutil.rmtree("./test_rag_db", ignore_errors=True)
        
        return True
        
    except Exception as e:
        print(f"❌ Error en test de sistema completo: {e}")
        import traceback
        traceback.print_exc()
        return False

async def run_all_tests():
    """Ejecuta todos los tests"""
    print("\n" + "🚀"*30)
    print("SUITE DE PRUEBAS - Sistema RAG ProfeGo")
    print("🚀"*30)
    
    results = {}
    
    # Test 1: Embeddings
    results['embeddings'] = await test_embeddings()
    
    # Test 2: Document Processor
    results['processor'] = test_document_processor()
    
    # Test 3: Vector Store
    results['vector_store'] = test_vector_store()
    
    # Test 4: Sistema completo
    results['full_system'] = await test_full_system()
    
    # Resumen
    print("\n" + "="*60)
    print("📊 RESUMEN DE PRUEBAS")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASÓ" if passed else "❌ FALLÓ"
        print(f"{status} - {test_name}")
    
    total = len(results)
    passed = sum(results.values())
    
    print("\n" + "="*60)
    print(f"🎯 Resultado: {passed}/{total} pruebas pasaron")
    print("="*60)
    
    if passed == total:
        print("\n🎉 ¡Todas las pruebas pasaron! El sistema RAG está listo.")
    else:
        print("\n⚠️  Algunas pruebas fallaron. Revisa los errores arriba.")

if __name__ == "__main__":
    asyncio.run(run_all_tests())