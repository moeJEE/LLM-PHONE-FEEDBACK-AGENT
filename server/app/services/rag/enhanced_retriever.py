"""
Enhanced RAG Retriever for Optimized Token Consumption
"""
import logging
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import asyncio
import openai
from datetime import datetime

from ...core.config import get_settings
from ...db.vectordb import VectorDB
from ...db.mongodb import MongoDB
from bson import ObjectId

logger = logging.getLogger(__name__)
settings = get_settings()

class RetrievalStrategy(Enum):
    SIMPLE = "simple"
    HYBRID = "hybrid"
    CONTEXTUAL = "contextual"
    ADAPTIVE = "adaptive"

@dataclass
class RetrievalContext:
    """Context for retrieval operations"""
    user_id: str
    domain: str = "general"
    conversation_history: List[Dict[str, Any]] = None
    document_filters: Optional[Dict[str, Any]] = None
    knowledge_base_id: Optional[str] = None

@dataclass
class RetrievalResult:
    """Enhanced retrieval result with optimization metadata"""
    content: str
    sources: List[str]
    tokens_used: int = 0
    documents: List[Dict[str, Any]] = None
    query_used: str = ""
    strategy_applied: RetrievalStrategy = RetrievalStrategy.SIMPLE
    relevance_scores: List[float] = None
    compression_ratio: float = 0.0
    tokens_saved: int = 0

class EnhancedRAGRetriever:
    """Enhanced RAG retriever with token optimization"""
    
    def __init__(self):
        self.vector_db = VectorDB()
        openai.api_key = settings.OPENAI_API_KEY
        self.client = openai.Client()
        self.max_chunk_tokens = 500  # Optimal chunk size
        self.overlap_tokens = 50     # Overlap between chunks
        
    async def retrieve_optimized_context(
        self,
        query: str,
        context: RetrievalContext,
        max_tokens: int = 2000,
        strategy: Optional[RetrievalStrategy] = None
    ) -> RetrievalResult:
        """Retrieve and optimize context for LLM consumption"""
        try:
            # Choose strategy if not specified
            if strategy is None:
                strategy = self._select_strategy(query, context)
            
            # Enhance query based on context
            enhanced_query = await self._enhance_query(query, context)
            
            # Get relevant documents from MongoDB first
            relevant_docs = await self._get_filtered_documents(context)
            
            if not relevant_docs:
                logger.warning(f"No relevant documents found for user {context.user_id}")
                return RetrievalResult(
                    content="",
                    sources=[],
                    tokens_used=0
                )
            
            # Search in vector collections of relevant documents
            search_results = await self._search_document_collections(enhanced_query, relevant_docs)
            
            if not search_results:
                logger.warning(f"No vector search results found for query: {enhanced_query}")
                return RetrievalResult(
                    content="",
                    sources=[],
                    tokens_used=0
                )
            
            # Remove duplicates and rank by relevance
            deduplicated_docs = self._deduplicate_documents(search_results)
            ranked_docs = self._rank_by_relevance(deduplicated_docs, enhanced_query)
            
            # Optimize for token limit
            optimized_docs, compression_ratio, tokens_saved = await self._optimize_for_tokens(
                ranked_docs, max_tokens
            )
            
            # Format the content for LLM
            formatted_content = self._format_search_results(optimized_docs)
            sources = list(set([doc.get('document_name', 'Unknown') for doc in optimized_docs]))
            
            return RetrievalResult(
                content=formatted_content,
                sources=sources,
                tokens_used=self._count_tokens(formatted_content),
                documents=optimized_docs,
                query_used=enhanced_query,
                strategy_applied=strategy,
                relevance_scores=[doc.get('relevance_score', 0.0) for doc in optimized_docs],
                compression_ratio=compression_ratio,
                tokens_saved=tokens_saved
            )
            
        except Exception as e:
            logger.error(f"Error in enhanced retrieval: {e}")
            # Fallback to empty result
            return RetrievalResult(
                content="",
                sources=[],
                tokens_used=0,
                query_used=query,
                strategy_applied=RetrievalStrategy.SIMPLE
            )
    
    async def _get_filtered_documents(self, context: RetrievalContext) -> List[Dict[str, Any]]:
        """Get documents filtered by context criteria"""
        try:
            documents_collection = MongoDB.get_collection("documents")
            
            # Build query based on context
            query = {
                "owner_id": context.user_id,
                "status": "processed",
                "vector_collection_name": {"$exists": True, "$ne": None}
            }
            
            # Handle specific knowledge base (document) selection
            if context.knowledge_base_id and context.knowledge_base_id not in ["general", "default", "none"]:
                try:
                    # Try to use knowledge_base_id as a specific document ID
                    from bson import ObjectId
                    query["_id"] = ObjectId(context.knowledge_base_id)
                    logger.info(f"🎯 Filtering to specific document: {context.knowledge_base_id}")
                except Exception:
                    # If not a valid ObjectId, try as document name
                    query["name"] = context.knowledge_base_id
                    logger.info(f"🎯 Filtering to document by name: {context.knowledge_base_id}")
            
            # Add additional document filters if provided
            if context.document_filters:
                # Only add filters that are valid document fields
                for key, value in context.document_filters.items():
                    if key in ["owner_id", "status", "document_type", "tags"]:
                        query[key] = value
            
            logger.info(f"Querying documents with: {query}")
            
            # Get documents
            docs = await documents_collection.find(query).to_list(length=50)
            
            logger.info(f"Found {len(docs)} filtered documents for user {context.user_id}")
            
            # Log document names for debugging
            if docs:
                doc_names = [doc.get("name", "Unknown") for doc in docs]
                logger.info(f"📚 Retrieved documents: {', '.join(doc_names)}")
            
            return docs
            
        except Exception as e:
            logger.error(f"Error getting filtered documents: {e}")
            return []
    
    async def _search_document_collections(self, query: str, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Search across multiple document vector collections"""
        try:
            from ...services.document_processor.embedding_generator import EmbeddingGenerator
            
            # Generate query embedding
            embedding_generator = EmbeddingGenerator()
            query_embedding = embedding_generator.generate_embeddings([query])[0]
            
            all_results = []
            
            # Search each document's vector collection
            for doc in documents:
                vector_collection_name = doc.get("vector_collection_name")
                if not vector_collection_name:
                    continue
                
                try:
                    # Search this document's vector collection
                    results = self.vector_db.similarity_search(
                        collection_name=vector_collection_name,
                        query_embedding=query_embedding,
                        top_k=5
                    )
                    
                    # Add document metadata to results
                    for result in results:
                        result['document_id'] = str(doc["_id"])
                        result['document_name'] = doc.get("name", "Unknown")
                        result['content'] = result.get('text', '')  # Normalize field name
                        all_results.append(result)
                        
                except Exception as e:
                    logger.error(f"Error searching vector collection {vector_collection_name}: {e}")
                    continue
            
            logger.info(f"Found {len(all_results)} total vector search results")
            return all_results
            
        except Exception as e:
            logger.error(f"Error in document collections search: {e}")
            return []
    
    def _format_search_results(self, results: List[Dict[str, Any]]) -> str:
        """Format search results into a readable content string"""
        if not results:
            return ""
        
        formatted_parts = []
        for i, result in enumerate(results, 1):
            content = result.get('content', result.get('text', ''))
            document_name = result.get('document_name', 'Unknown')
            score = result.get('score', 0.0)
            
            formatted_parts.append(f"### Source {i}: {document_name} (Relevance: {score:.2f})\n{content}\n")
        
        return "\n".join(formatted_parts)

    async def _enhance_query(self, query: str, context: RetrievalContext) -> str:
        """Enhance query using conversation context"""
        try:
            if not context.conversation_history:
                return query
            
            # Build context from conversation history
            history_context = self._format_conversation_history(context.conversation_history)
            
            enhancement_prompt = f"""
Given this conversation context and current query, create an enhanced search query that captures the full intent:

Conversation Context:
{history_context}

Current Query: {query}

Enhanced Query (single line, keywords focused):"""
            
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": enhancement_prompt}],
                temperature=0.3,
                max_tokens=100
            )
            
            enhanced = response.choices[0].message.content.strip()
            return enhanced if enhanced else query
            
        except Exception as e:
            logger.error(f"Error enhancing query: {e}")
            return query
    
    async def _simple_retrieval(self, query: str) -> List[Dict[str, Any]]:
        """Simple similarity search"""
        try:
            results = await self.vector_db.similarity_search(query, top_k=5)
            return results
        except Exception as e:
            logger.error(f"Error in simple retrieval: {e}")
            return []
    
    async def _hybrid_retrieval(self, query: str, context: RetrievalContext) -> List[Dict[str, Any]]:
        """Hybrid retrieval combining multiple approaches"""
        try:
            # Get semantic results
            semantic_results = await self.vector_db.similarity_search(query, top_k=3)
            
            # Get keyword-based results (if available)
            keyword_results = await self.vector_db.similarity_search(
                query.replace(" ", " AND "), top_k=2
            )
            
            # Combine and deduplicate
            combined = semantic_results + keyword_results
            return self._deduplicate_documents(combined)
            
        except Exception as e:
            logger.error(f"Error in hybrid retrieval: {e}")
            return await self._simple_retrieval(query)
    
    async def _contextual_retrieval(self, query: str, context: RetrievalContext) -> List[Dict[str, Any]]:
        """Context-aware retrieval using conversation history"""
        try:
            # Build contextual query
            if context.conversation_history:
                recent_topics = self._extract_topics(context.conversation_history[-3:])
                contextual_query = f"{query} {' '.join(recent_topics)}"
            else:
                contextual_query = query
            
            results = await self.vector_db.similarity_search(contextual_query, top_k=5)
            return results
            
        except Exception as e:
            logger.error(f"Error in contextual retrieval: {e}")
            return await self._simple_retrieval(query)
    
    async def _adaptive_retrieval(self, query: str, context: RetrievalContext) -> List[Dict[str, Any]]:
        """Adaptive retrieval that adjusts based on context"""
        try:
            # Analyze query characteristics
            query_type = self._analyze_query(query)
            
            if query_type == "specific":
                return await self._simple_retrieval(query)
            elif query_type == "broad":
                return await self._hybrid_retrieval(query, context)
            else:
                return await self._contextual_retrieval(query, context)
                
        except Exception as e:
            logger.error(f"Error in adaptive retrieval: {e}")
            return await self._simple_retrieval(query)
    
    def _select_strategy(self, query: str, context: RetrievalContext) -> RetrievalStrategy:
        """Select the best retrieval strategy based on query and context"""
        # Simple heuristics for strategy selection
        if len(query.split()) <= 3:
            return RetrievalStrategy.SIMPLE
        elif context.conversation_history and len(context.conversation_history) > 2:
            return RetrievalStrategy.CONTEXTUAL
        elif len(query.split()) > 8:
            return RetrievalStrategy.HYBRID
        else:
            return RetrievalStrategy.ADAPTIVE
    
    def _deduplicate_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate documents based on content similarity"""
        if not documents:
            return []
        
        unique_docs = []
        seen_content = set()
        
        for doc in documents:
            content = doc.get('content', '')
            # Simple deduplication based on first 100 characters
            content_key = content[:100].lower().strip()
            
            if content_key not in seen_content:
                seen_content.add(content_key)
                unique_docs.append(doc)
        
        return unique_docs
    
    def _rank_by_relevance(self, documents: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Rank documents by relevance to query"""
        for doc in documents:
            # Simple relevance scoring based on keyword overlap
            doc_content = doc.get('content', '').lower()
            query_words = set(query.lower().split())
            doc_words = set(doc_content.split())
            
            overlap = len(query_words & doc_words)
            doc['relevance_score'] = overlap / max(len(query_words), 1)
        
        return sorted(documents, key=lambda x: x.get('relevance_score', 0), reverse=True)
    
    async def _optimize_for_tokens(
        self, 
        documents: List[Dict[str, Any]], 
        max_tokens: int
    ) -> Tuple[List[Dict[str, Any]], float, int]:
        """Optimize document selection and compression for token limits"""
        try:
            optimized_docs = []
            current_tokens = 0
            original_tokens = 0
            
            for doc in documents:
                content = doc.get('content', '')
                doc_tokens = self._count_tokens(content)
                original_tokens += doc_tokens
                
                if current_tokens + doc_tokens <= max_tokens:
                    optimized_docs.append(doc)
                    current_tokens += doc_tokens
                else:
                    # Try to compress the document
                    remaining_tokens = max_tokens - current_tokens
                    if remaining_tokens > 100:  # Minimum useful size
                        compressed_content = await self._compress_document(content, remaining_tokens)
                        if compressed_content:
                            compressed_doc = doc.copy()
                            compressed_doc['content'] = compressed_content
                            compressed_doc['compressed'] = True
                            optimized_docs.append(compressed_doc)
                            current_tokens += self._count_tokens(compressed_content)
                    break
            
            compression_ratio = current_tokens / max(original_tokens, 1)
            tokens_saved = original_tokens - current_tokens
            
            return optimized_docs, compression_ratio, tokens_saved
            
        except Exception as e:
            logger.error(f"Error optimizing for tokens: {e}")
            return documents[:3], 1.0, 0
    
    async def _compress_document(self, content: str, target_tokens: int) -> Optional[str]:
        """Compress document content using LLM"""
        try:
            compression_prompt = f"""
Compress the following text to approximately {target_tokens} tokens while preserving key information:

{content}

Compressed version:"""
            
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": compression_prompt}],
                temperature=0.3,
                max_tokens=target_tokens
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error compressing document: {e}")
            return None
    
    def _count_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        return max(1, len(text) // 4)  # Rough approximation
    
    def _format_conversation_history(self, history: List[Dict[str, Any]]) -> str:
        """Format conversation history for context"""
        formatted = []
        for item in history[-3:]:  # Last 3 items
            if isinstance(item, dict):
                role = item.get('role', 'user')
                content = item.get('content', str(item))
                formatted.append(f"{role}: {content}")
            else:
                formatted.append(str(item))
        return "\n".join(formatted)
    
    def _extract_topics(self, conversation_items: List[Dict[str, Any]]) -> List[str]:
        """Extract key topics from conversation items"""
        topics = []
        for item in conversation_items:
            if isinstance(item, dict):
                content = item.get('content', '')
                # Simple keyword extraction
                words = content.split()
                topics.extend([word for word in words if len(word) > 4])
        return list(set(topics))[:5]  # Limit to 5 unique topics
    
    def _analyze_query(self, query: str) -> str:
        """Analyze query characteristics"""
        words = query.split()
        if len(words) <= 3:
            return "specific"
        elif len(words) > 8:
            return "broad"
        else:
            return "general" 