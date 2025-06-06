// src/services/api.js
import { SignIn } from '@clerk/clerk-react';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

/**
 * API service for making authenticated requests
 */
class ApiService {
  /**
   * Make an authenticated API request
   * @param {string} endpoint - API endpoint
   * @param {Object} options - Fetch options
   * @param {string|null} token - Authentication token
   * @returns {Promise<any>} - Response data
   */
  static async request(endpoint, options = {}, token = null) {
    try {
      const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
      };
      
      // Add authorization header if token exists
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
      
      const url = `${API_BASE_URL}${endpoint}`;

      const response = await fetch(url, {
        ...options,
        headers,
      });
      
      // Handle token expiration
      if (response.status === 401) {
        throw new Error('Authentication failed. Please login again.');
      }

      // Try to parse JSON response
      let data;
      const contentType = response.headers.get('content-type');
      
      if (contentType && contentType.includes('application/json')) {
        try {
          data = await response.json();
        } catch (parseError) {
          throw new Error('Invalid JSON response from server');
        }
      } else {
        // Handle non-JSON responses
        const textResponse = await response.text();
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${textResponse || response.statusText}`);
        }
        
        return textResponse;
      }
      
      // Check if request was successful
      if (!response.ok) {
        const errorMessage = data?.detail || data?.error || data?.message || `HTTP ${response.status}: ${response.statusText}`;
        throw new Error(errorMessage);
      }
      
      return data;
    } catch (error) {
      // Enhanced error handling
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        throw new Error('Network error. Please check your connection and try again.');
      }
      
      throw error;
    }
  }
  
  /**
   * GET request
   * @param {string} endpoint - API endpoint
   * @param {Object} options - Additional fetch options
   * @param {string|null} token - Authentication token
   * @returns {Promise<any>} - Response data
   */
  static async get(endpoint, options = {}, token = null) {
    return this.request(endpoint, {
      method: 'GET',
      ...options,
    }, token);
  }
  
  /**
   * POST request
   * @param {string} endpoint - API endpoint
   * @param {Object} data - Request body data
   * @param {Object} options - Additional fetch options
   * @param {string|null} token - Authentication token
   * @returns {Promise<any>} - Response data
   */
  static async post(endpoint, data, options = {}, token = null) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
      ...options,
    }, token);
  }
  
  /**
   * PUT request
   * @param {string} endpoint - API endpoint
   * @param {Object} data - Request body data
   * @param {Object} options - Additional fetch options
   * @param {string|null} token - Authentication token
   * @returns {Promise<any>} - Response data
   */
  static async put(endpoint, data, options = {}, token = null) {
    return this.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
      ...options,
    }, token);
  }
  
  /**
   * DELETE request
   * @param {string} endpoint - API endpoint
   * @param {Object} options - Additional fetch options
   * @param {string|null} token - Authentication token
   * @returns {Promise<any>} - Response data
   */
  static async delete(endpoint, options = {}, token = null) {
    return this.request(endpoint, {
      method: 'DELETE',
      ...options,
    }, token);
  }
}

// Export the static service as default
export default ApiService;

/**
 * Test backend connection (does not require authentication)
 */
export async function checkBackendConnection() {
  try {
    const baseUrl = API_BASE_URL.replace(/\/+$/, '');
    const healthUrl = `${baseUrl}/health`;
    
    const response = await fetch(healthUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 5000, // 5 second timeout
    });

    if (!response.ok) {
      throw new Error(`Health check failed: ${response.status}`);
    }

    const data = await response.json();
    return { success: true, data };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * Call Management API functions
 */

/**
 * Get all calls with optional filtering
 * @param {Object} filters - Filter options (status, date_range, etc.)
 * @param {string|null} token - Authentication token
 * @returns {Promise<Object>} - Calls data grouped by status
 */
export async function getCalls(filters = {}, token = null) {
  try {
    const queryParams = new URLSearchParams();
    
    // Add filters to query params
    Object.entries(filters).forEach(([key, value]) => {
      if (value && value !== 'all') {
        queryParams.append(key, value);
      }
    });
    
    const endpoint = `/api/calls?${queryParams.toString()}`;
    return await ApiService.get(endpoint, {}, token);
  } catch (error) {
    throw new Error(`Failed to fetch calls: ${error.message}`);
  }
}

/**
 * Get call statistics
 * @param {string} period - Time period (all, week, month, year)
 * @param {string|null} token - Authentication token
 * @returns {Promise<Object>} - Call statistics
 */
export async function getCallStats(period = 'all', token = null) {
  try {
    const endpoint = `/api/calls/stats?period=${period}`;
    return await ApiService.get(endpoint, {}, token);
  } catch (error) {
    throw new Error(`Failed to fetch call stats: ${error.message}`);
  }
}

/**
 * Get a specific call by ID
 * @param {string} callId - Call ID
 * @param {string|null} token - Authentication token
 * @returns {Promise<Object>} - Call details
 */
export async function getCallById(callId, token = null) {
  try {
    const endpoint = `/api/calls/${callId}`;
    return await ApiService.get(endpoint, {}, token);
  } catch (error) {
    throw new Error(`Failed to fetch call details: ${error.message}`);
  }
}

/**
 * Create a new call
 * @param {Object} callData - Call data
 * @param {string|null} token - Authentication token
 * @param {boolean} sendWhatsAppSurvey - Whether to send WhatsApp survey
 * @param {boolean} knowledgeBaseOnly - Whether to use knowledge base only
 * @returns {Promise<Object>} - Created call data
 */
export async function createCall(callData, token = null, sendWhatsAppSurvey = false, knowledgeBaseOnly = false) {
  try {
    const endpoint = '/api/calls/';
    const data = {
      ...callData,
      send_whatsapp_survey: sendWhatsAppSurvey,
      knowledge_base_only: knowledgeBaseOnly,
    };
    
    return await ApiService.post(endpoint, data, {}, token);
  } catch (error) {
    throw new Error(`Failed to create call: ${error.message}`);
  }
}

/**
 * Update an existing call
 * @param {string} callId - Call ID
 * @param {Object} updateData - Data to update
 * @param {string|null} token - Authentication token
 * @returns {Promise<Object>} - Updated call data
 */
export async function updateCall(callId, updateData, token = null) {
  try {
    const endpoint = `/api/calls/${callId}`;
    return await ApiService.put(endpoint, updateData, {}, token);
  } catch (error) {
    throw new Error(`Failed to update call: ${error.message}`);
  }
}

/**
 * Delete a call
 * @param {string} callId - Call ID
 * @param {string|null} token - Authentication token
 * @returns {Promise<Object>} - Deletion confirmation
 */
export async function deleteCall(callId, token = null) {
  try {
    const endpoint = `/api/calls/${callId}`;
    return await ApiService.delete(endpoint, {}, token);
  } catch (error) {
    throw new Error(`Failed to delete call: ${error.message}`);
  }
}

/**
 * Get survey results for a call
 * @param {string} callId - Call ID
 * @param {string|null} token - Authentication token
 * @returns {Promise<Object>} - Survey results
 */
export async function getCallSurveyResults(callId, token = null) {
  try {
    const endpoint = `/api/calls/${callId}/survey-results`;
    return await ApiService.get(endpoint, {}, token);
  } catch (error) {
    throw new Error(`Failed to fetch survey results: ${error.message}`);
  }
}

/**
 * Get survey statistics
 * @param {string|null} token - Authentication token
 * @returns {Promise<Object>} - Survey statistics
 */
export async function getSurveyStats(token = null) {
  try {
    const endpoint = '/api/surveys/stats';
    return await ApiService.get(endpoint, {}, token);
  } catch (error) {
    throw new Error(`Failed to fetch survey stats: ${error.message}`);
  }
}

/**
 * Dashboard Analytics API functions
 */

/**
 * Get dashboard analytics
 * @param {string} period - Time period (week, month, year)
 * @param {string|null} token - Authentication token
 * @returns {Promise<Object>} - Dashboard analytics
 */
export async function getDashboardAnalytics(period = 'month', token = null) {
  try {
    const endpoint = `/api/analytics/dashboard?period=${period}`;
    const data = await ApiService.get(endpoint, {}, token);
    
    return {
      callStats: data.call_stats || {},
      callsByStatus: data.calls_by_status || [],
      callTrends: data.call_trends || [],
      ...data
    };
  } catch (error) {
    throw new Error(`Failed to fetch dashboard analytics: ${error.message}`);
  }
}

/**
 * Get sentiment analytics
 * @param {string} period - Time period (week, month, year)
 * @param {string|null} token - Authentication token
 * @returns {Promise<Object>} - Sentiment analytics
 */
export async function getSentimentAnalytics(period = 'month', token = null) {
  try {
    const endpoint = `/api/analytics/sentiment?period=${period}`;
    const data = await ApiService.get(endpoint, {}, token);
    
    return {
      sentimentDistribution: data.sentiment_distribution || [],
      sentimentTrends: data.sentiment_trends || [],
      ...data
    };
  } catch (error) {
    throw new Error(`Failed to fetch sentiment analytics: ${error.message}`);
  }
}

/**
 * Get call volume analytics for dashboard charts
 * @param {string} period - Time period for analysis
 * @param {string|null} token - Authentication token
 * @returns {Promise<Object>} - Call volume data
 */
export async function getCallVolumeAnalytics(period = 'week', token = null) {
  try {
    const calls = await getCalls({ limit: 100 }, token);
    
    // Process calls to get volume data by time period
    const volumeData = processCallVolumeData(calls, period);
    
    return volumeData;
  } catch (error) {
    throw new Error(`Failed to fetch call volume analytics: ${error.message}`);
  }
}

/**
 * Helper function to process sentiment data from calls
 * @param {Array} calls - Array of calls
 * @param {string} period - Time period
 * @returns {Array} - Processed sentiment data for charts
 */
function processSentimentData(calls, period) {
  const sentimentByPeriod = {};
  const now = new Date();
  
  // Ensure calls is an array
  if (!Array.isArray(calls)) {
    calls = [];
  }
  
  // Initialize periods based on timeframe
  let periods = [];
  if (period === 'week') {
    for (let i = 6; i >= 0; i--) {
      const date = new Date(now);
      date.setDate(date.getDate() - i);
      periods.push(date.toLocaleDateString('en-US', { weekday: 'short' }));
    }
  } else if (period === 'month') {
    for (let i = 11; i >= 0; i--) {
      const date = new Date(now);
      date.setMonth(date.getMonth() - i);
      periods.push(date.toLocaleDateString('en-US', { month: 'short' }));
    }
  }
  
  // Initialize sentiment data structure
  periods.forEach(period => {
    sentimentByPeriod[period] = { positive: 0, neutral: 0, negative: 0, total: 0 };
  });
  
  // Process calls with sentiment data
  calls.forEach(call => {
    if (call && call.metadata && call.metadata.overall_sentiment !== undefined && call.created_at) {
      const callDate = new Date(call.created_at);
      let periodKey;
      
      if (period === 'week') {
        periodKey = callDate.toLocaleDateString('en-US', { weekday: 'short' });
      } else if (period === 'month') {
        periodKey = callDate.toLocaleDateString('en-US', { month: 'short' });
      }
      
      if (sentimentByPeriod[periodKey]) {
        const sentiment = call.metadata.overall_sentiment;
        if (sentiment > 0.1) {
          sentimentByPeriod[periodKey].positive++;
        } else if (sentiment < -0.1) {
          sentimentByPeriod[periodKey].negative++;
        } else {
          sentimentByPeriod[periodKey].neutral++;
        }
        sentimentByPeriod[periodKey].total++;
      }
    }
  });
  
  // Convert to chart format with percentages
  return periods.map(period => {
    const data = sentimentByPeriod[period];
    const total = data.total || 1; // Avoid division by zero
    
    return {
      name: period,
      positive: Math.round((data.positive / total) * 100),
      neutral: Math.round((data.neutral / total) * 100),
      negative: Math.round((data.negative / total) * 100)
    };
  });
}

/**
 * Helper function to process call volume data
 * @param {Array} calls - Array of calls
 * @param {string} period - Time period
 * @returns {Array} - Processed volume data for charts
 */
function processCallVolumeData(calls, period) {
  const volumeByPeriod = {};
  const now = new Date();
  
  // Ensure calls is an array
  if (!Array.isArray(calls)) {
    calls = [];
  }
  
  // Initialize periods
  let periods = [];
  if (period === 'week') {
    for (let i = 6; i >= 0; i--) {
      const date = new Date(now);
      date.setDate(date.getDate() - i);
      periods.push(date.toLocaleDateString('en-US', { weekday: 'short' }));
    }
  }
  
  // Initialize volume data structure
  periods.forEach(period => {
    volumeByPeriod[period] = { inbound: 0, outbound: 0 };
  });
  
  // Process calls
  calls.forEach(call => {
    if (call && call.created_at) {
      const callDate = new Date(call.created_at);
      let periodKey;
      
      if (period === 'week') {
        periodKey = callDate.toLocaleDateString('en-US', { weekday: 'short' });
      }
      
      if (volumeByPeriod[periodKey]) {
        // Determine call direction based on call type or status
        if (call.call_type === 'inbound' || (call.phone_number && call.phone_number.includes('inbound'))) {
          volumeByPeriod[periodKey].inbound++;
        } else {
          volumeByPeriod[periodKey].outbound++;
        }
      }
    }
  });
  
  return periods.map(period => ({
    name: period,
    inbound: volumeByPeriod[period].inbound,
    outbound: volumeByPeriod[period].outbound
  }));
}

/**
 * Initiate a call
 * @param {Object} callData - Call data
 * @param {string|null} token - Authentication token
 * @returns {Promise<Object>} - Initiated call
 */
export async function initiateCall(callData, token = null) {
  try {
    return await ApiService.post('/calls/initiate', callData, {}, token);
  } catch (error) {
    throw new Error(`Failed to initiate call: ${error.message}`);
  }
}

/**
 * Knowledge Base API functions
 */

/**
 * Get all documents with optional filtering
 * @param {Object} filters - Filter options (status, document_type, tag, skip, limit)
 * @param {string|null} token - Authentication token
 * @returns {Promise<Array>} - Array of documents
 */
export async function getDocuments(filters = {}, token = null) {
  try {
    const queryParams = new URLSearchParams();
    
    // Add filters to query params
    if (filters.status) queryParams.append('status', filters.status);
    if (filters.document_type) queryParams.append('document_type', filters.document_type);
    if (filters.tag) queryParams.append('tag', filters.tag);
    if (filters.skip) queryParams.append('skip', filters.skip.toString());
    if (filters.limit) queryParams.append('limit', filters.limit.toString());
    
    const endpoint = `/knowledge${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
    return await ApiService.get(endpoint, {}, token);
  } catch (error) {
    throw new Error(`Failed to fetch documents: ${error.message}`);
  }
}

/**
 * Get document by ID
 * @param {string} documentId - Document ID
 * @param {string|null} token - Authentication token
 * @returns {Promise<Object>} - Document data
 */
export async function getDocumentById(documentId, token = null) {
  try {
    return await ApiService.get(`/knowledge/${documentId}`, {}, token);
  } catch (error) {
    throw new Error(`Failed to fetch document: ${error.message}`);
  }
}

/**
 * Upload document to knowledge base
 * @param {FormData} formData - Form data with file and metadata
 * @param {string|null} token - Authentication token
 * @returns {Promise<Object>} - Upload result
 */
export async function uploadDocument(formData, token = null) {
  try {
    return await ApiService.post('/knowledge/upload', formData, {
      'Content-Type': undefined, // Let browser set content type for FormData
    }, token);
  } catch (error) {
    throw new Error(`Failed to upload document: ${error.message}`);
  }
}

/**
 * Delete document from knowledge base
 * @param {string} documentId - Document ID
 * @param {string|null} token - Authentication token
 * @returns {Promise<void>}
 */
export async function deleteDocument(documentId, token = null) {
  try {
    return await ApiService.delete(`/knowledge/${documentId}`, {}, token);
  } catch (error) {
    throw new Error(`Failed to delete document: ${error.message}`);
  }
}

/**
 * Update document metadata
 * @param {string} documentId - Document ID
 * @param {Object} updateData - Update data
 * @param {string|null} token - Authentication token
 * @returns {Promise<Object>} - Updated document
 */
export async function updateDocument(documentId, updateData, token = null) {
  try {
    return await ApiService.put(`/knowledge/${documentId}`, updateData, {}, token);
  } catch (error) {
    throw new Error(`Failed to update document: ${error.message}`);
  }
}

/**
 * Search documents in knowledge base
 * @param {string} searchQuery - Search query
 * @param {string|null} token - Authentication token
 * @returns {Promise<Array>} - Search results
 */
export async function searchDocuments(searchQuery, token = null) {
  try {
    return await ApiService.post('/knowledge/search', { query: searchQuery }, {}, token);
  } catch (error) {
    throw new Error(`Failed to search documents: ${error.message}`);
  }
}

/**
 * Create knowledge inquiry
 * @param {Object} inquiryData - Inquiry data
 * @param {string|null} token - Authentication token
 * @returns {Promise<Object>} - Created inquiry
 */
export async function createKnowledgeInquiry(inquiryData, token = null) {
  try {
    return await ApiService.post('/knowledge/inquiries', inquiryData, {}, token);
  } catch (error) {
    throw new Error(`Failed to create knowledge inquiry: ${error.message}`);
  }
}

// Optimization API endpoints
export const optimizationAPI = {
  getTokenAnalytics: (days = 7, token = null) =>
    ApiService.get(`/optimization/analytics?days=${days}`, {}, token),

  getOptimizationInsights: (token = null) =>
    ApiService.get('/optimization/insights', {}, token),

  getCostBreakdown: (days = 30, token = null) =>
    ApiService.get(`/optimization/cost-breakdown?days=${days}`, {}, token),

  getRagPerformance: (days = 7, token = null) =>
    ApiService.get(`/optimization/rag-performance?days=${days}`, {}, token),

  applyRecommendation: (type, token = null) =>
    ApiService.post('/optimization/apply-recommendation', { recommendation_type: type }, {}, token),

  testOptimization: (testType, sampleSize = 10, token = null) =>
    ApiService.post(`/optimization/test-optimization?test_type=${testType}&sample_size=${sampleSize}`, {}, {}, token),

  createRealData: (token = null) =>
    ApiService.post('/optimization/create-real-data', {}, {}, token),
};