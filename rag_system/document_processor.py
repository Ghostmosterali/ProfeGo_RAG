"""
Procesador de documentos para el sistema RAG
VERSIÓN ULTRA LIGERA - SOLO ARCHIVOS TXT
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Optional
import tempfile
import gc

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """
    Procesa documentos para el sistema RAG
    Divide textos en chunks y extrae metadata
    VERSIÓN OPTIMIZADA PARA MEMORIA
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ):
        """
        Inicializa el procesador de documentos
        
        Args:
            chunk_size: Tamaño máximo de cada chunk en caracteres
            chunk_overlap: Cantidad de solapamiento entre chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        logger.info(f"DocumentProcessor inicializado (chunk_size={chunk_size}, overlap={chunk_overlap})")
    
    def extract_text_from_file(self, file_path: str) -> Optional[str]:
        """
        Extrae texto de un archivo
        SOLO SOPORTA .TXT POR AHORA (sin OCR para evitar problemas de memoria)
        
        Args:
            file_path: Ruta al archivo
            
        Returns:
            Texto extraído o None si falla
        """
        file_path_obj = Path(file_path)
        
        # SOLO archivos .txt por ahora
        if file_path_obj.suffix.lower() != '.txt':
            logger.warning(f"Archivo {file_path_obj.name} ignorado (solo se procesan .txt por ahora)")
            return None
        
        # Leer archivo .txt directamente
        try:
            # Intentar UTF-8 primero
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            logger.info(f"Texto leido de {file_path_obj.name}: {len(text)} caracteres")
            return text
        except UnicodeDecodeError:
            # Si falla UTF-8, intentar con latin-1
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    text = f.read()
                logger.info(f"Texto leido (latin-1) de {file_path_obj.name}: {len(text)} caracteres")
                return text
            except Exception as e:
                logger.error(f"Error leyendo archivo TXT: {e}")
                return None
        except Exception as e:
            logger.error(f"Error procesando archivo {file_path}: {e}")
            return None
    
    def extract_text_from_bytes(self, content: bytes, filename: str) -> Optional[str]:
        """
        Extrae texto de un archivo en bytes
        
        Args:
            content: Contenido del archivo en bytes
            filename: Nombre del archivo (para determinar extensión)
            
        Returns:
            Texto extraído o None si falla
        """
        file_path_obj = Path(filename)
        
        # SOLO .txt por ahora
        if file_path_obj.suffix.lower() != '.txt':
            logger.warning(f"Archivo {filename} ignorado (solo se procesan .txt por ahora)")
            return None
        
        try:
            # Intentar decodificar como UTF-8
            try:
                text = content.decode('utf-8')
                logger.info(f"Texto decodificado de {filename}: {len(text)} caracteres")
                return text
            except UnicodeDecodeError:
                # Intentar con latin-1
                text = content.decode('latin-1')
                logger.info(f"Texto decodificado (latin-1) de {filename}: {len(text)} caracteres")
                return text
        except Exception as e:
            logger.error(f"Error decodificando bytes: {e}")
            return None
    
    def split_text_into_chunks(
        self,
        text: str,
        metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Divide texto en chunks con solapamiento
        VERSIÓN ULTRA SIMPLE
        
        Args:
            text: Texto a dividir
            metadata: Metadata adicional para cada chunk
            
        Returns:
            Lista de chunks con metadata
        """
        if not text or not text.strip():
            return []
        
        chunks = []
        text_length = len(text)
        
        # Si el texto es pequeño, retornarlo como un solo chunk
        if text_length <= self.chunk_size:
            chunk_data = {
                'text': text.strip(),
                'chunk_id': 0,
                'start_char': 0,
                'end_char': text_length,
                **(metadata or {})
            }
            chunks.append(chunk_data)
            logger.info(f"Texto pequeño - 1 chunk creado")
            return chunks
        
        # Dividir texto en chunks simples
        chunk_id = 0
        for start in range(0, text_length, self.chunk_size - self.chunk_overlap):
            end = min(start + self.chunk_size, text_length)
            chunk_text = text[start:end].strip()
            
            if chunk_text:
                chunk_data = {
                    'text': chunk_text,
                    'chunk_id': chunk_id,
                    'start_char': start,
                    'end_char': end,
                    **(metadata or {})
                }
                chunks.append(chunk_data)
                chunk_id += 1
            
            # Si llegamos al final, salir
            if end >= text_length:
                break
        
        logger.info(f"Texto dividido en {len(chunks)} chunks")
        return chunks
    
    def process_document(
        self,
        file_path: str,
        document_type: str,
        metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Procesa un documento completo: extrae texto y divide en chunks
        
        Args:
            file_path: Ruta al archivo
            document_type: Tipo de documento (plan, diagnostico, cuento, cancion)
            metadata: Metadata adicional
            
        Returns:
            Lista de chunks procesados
        """
        logger.info(f"Procesando: {Path(file_path).name}")
        
        # Extraer texto
        text = self.extract_text_from_file(file_path)
        
        if not text:
            logger.warning(f"No se pudo extraer texto de {file_path}")
            return []
        
        # Preparar metadata
        doc_metadata = {
            'filename': Path(file_path).name,
            'document_type': document_type,
            'file_path': file_path,
            **(metadata or {})
        }
        
        # Dividir en chunks
        chunks = self.split_text_into_chunks(text, doc_metadata)
        
        # Liberar memoria del texto original
        del text
        gc.collect()
        
        logger.info(f"Documento procesado: {Path(file_path).name} -> {len(chunks)} chunks")
        
        return chunks
    
    def process_directory(
        self,
        directory_path: str,
        document_type: str,
        recursive: bool = False
    ) -> List[Dict]:
        """
        Procesa todos los documentos en un directorio
        SOLO ARCHIVOS .TXT POR AHORA
        
        Args:
            directory_path: Ruta al directorio
            document_type: Tipo de documentos (cuento, cancion, etc.)
            recursive: Si True, procesa subdirectorios
            
        Returns:
            Lista de todos los chunks procesados
        """
        all_chunks = []
        directory = Path(directory_path)
        
        if not directory.exists():
            logger.warning(f"Directorio no existe: {directory_path}")
            return []
        
        # SOLO archivos .txt por ahora para evitar problemas de memoria
        extensions = {'.txt'}
        
        # Buscar archivos
        if recursive:
            files = [f for f in directory.rglob('*') if f.suffix.lower() in extensions]
        else:
            files = [f for f in directory.glob('*') if f.suffix.lower() in extensions]
        
        logger.info(f"Procesando directorio {directory_path}: {len(files)} archivos .txt encontrados")
        
        if len(files) == 0:
            logger.warning(f"No se encontraron archivos .txt en {directory_path}")
            logger.info("Por ahora solo se procesan archivos .txt para evitar problemas de memoria")
            return []
        
        # Procesar archivo por archivo
        for idx, file_path in enumerate(files, 1):
            logger.info(f"Procesando archivo {idx}/{len(files)}: {file_path.name}")
            
            try:
                chunks = self.process_document(
                    str(file_path),
                    document_type,
                    metadata={'source_directory': directory_path}
                )
                all_chunks.extend(chunks)
                
                # Liberar memoria cada archivo
                gc.collect()
                    
            except Exception as e:
                logger.error(f"Error procesando {file_path.name}: {e}")
                # Continuar con el siguiente archivo
                continue
        
        logger.info(f"Directorio procesado: {len(all_chunks)} chunks totales de {len(files)} archivos")
        
        return all_chunks