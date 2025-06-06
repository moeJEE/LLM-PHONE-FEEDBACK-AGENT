// src/services/api.js
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api';

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
      console.log(`Making ${options.method || 'GET'} request to: ${url}`);

      const response = await fetch(url, {
        ...options,
        headers,
      });

      console.log(`Response status: ${response.status} ${response.statusText}`);
      
      // Handle token expiration
      if (response.status === 401) {
        console.warn('Authentication token expired or invalid');
        throw new Error('Authentication failed. Please login again.');
      }

      // Try to parse JSON response
      let data;
      const contentType = response.headers.get('content-type');
      
      if (contentType && contentType.includes('application/json')) {
        try {
          data = await response.json();
        } catch (parseError) {
          console.error('Failed to parse JSON response:', parseError);
          throw new Error('Invalid JSON response from server');
        }
      } else {
        // Handle non-JSON responses
        const textResponse = await response.text();
        console.log('Non-JSON response:', textResponse);
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${textResponse || response.statusText}`);
        }
        
        return textResponse;
      }
      
      // Check if request was successful
      if (!response.ok) {
        const errorMessage = data?.detail || data?.error || data?.message || `HTTP ${response.status}: ${response.statusText}`;
        console.error(`API error (${response.status}):`, errorMessage);
        throw new Error(errorMessage);
      }
      
      console.log(`API call successful:`, data);
      return data;
    } catch (error) {
      // Enhanced error logging
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        console.error(`Network error for ${endpoint}:`, error.message);
        throw new Error('Network error. Please check your connection and try again.');
      }
      
      console.error(`API error (${endpoint}):`, error.message);
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
export const testBackendConnection = async () => {
  try {
    // Utilisez l'URL de base sans "/api" pour l'endpoint /health
    const baseUrl = API_BASE_URL.split('/api')[0]; // Extrait la partie avant '/api'
    const healthUrl = `${baseUrl}/health`;
    
    console.log('API_BASE_URL:', API_BASE_URL);
    console.log('baseUrl:', baseUrl);
    console.log('Testing connection to:', healthUrl);
    
    const response = await fetch(healthUrl, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
      // Important en cas de problème CORS
      mode: 'cors'
    });
    
    if (!response.ok) {
      throw new Error(`Health check failed with status ${response.status}`);
    }
    
    const data = await response.json();
    console.log('Backend connection test successful:', data);
    return data;
  } catch (error) {
    console.error('Backend connection failed:', error);
    throw error;
  }
};

/**
 * Call Management API functions
 */

/**
 * Get all calls with optional filtering
 * @param {Object} filters - Filter options (status, date_range, etc.)
 * @param {string|null} token - Authentication token
 * @returns {Promise<Object>} - Calls data grouped by status
 */
export const getCalls = async (filters = {}, token = null) => {
  try {
    const queryParams = new URLSearchParams();
    
    // Add filters to query params
    Object.entries(filters).forEach(([key, value]) => {
      if (value && value !== 'all') {
        queryParams.append(key, value);
      }
    });
    
    const endpoint = `/calls/${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
    return await ApiService.get(endpoint, {}, token);
  } catch (error) {
    console.error('Error fetching calls:', error);
    throw error;
  }
};

/**
 * Get call statistics
 * @param {string} period - Stats period: 'today', 'week', 'month', 'all'
 * @param {string|null} token - Authentication token
 * @returns {Promise<Object>} - Call statistics
 */
export const getCallStats = async (period = 'all', token = null) => {
  try {
    const queryParams = new URLSearchParams();
    if (period && period !== 'all') {
      queryParams.append('period', period);
    }
    const endpoint = `/calls/stats/summary${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
    return await ApiService.get(endpoint, {}, token);
  } catch (error) {
    console.error('Error fetching call stats:', error);
    throw error;
  }
};

/**
 * Get a specific call by ID
 * @param {string} callId - Call ID
 * @param {string|null} token - Authentication token
 * @returns {Promise<Object>} - Call details
 */
export const getCallById = async (callId, token = null) => {
  try {
    return await ApiService.get(`/calls/${callId}`, {}, token);
  } catch (error) {
    console.error('Error fetching call details:', error);
    throw error;
  }
};

/**
 * Create a new call
 * @param {Object} callData - Call data
 * @param {string|null} token - Authentication token
 * @param {boolean} sendWhatsAppSurvey - Send WhatsApp survey immediately
 * @param {boolean} knowledgeBaseOnly - Use knowledge base only without survey
 * @returns {Promise<Object>} - Created call
 */
export const createCall = async (callData, token = null, sendWhatsAppSurvey = false, knowledgeBaseOnly = false) => {
  try {
    const params = new URLSearchParams();
    if (sendWhatsAppSurvey) {
      params.append('send_whatsapp_survey', 'true');
    }
    if (knowledgeBaseOnly) {
      params.append('knowledge_base_only', 'true');
    }
    
    const url = `/calls/${params.toString() ? '?' + params.toString() : ''}`;
    return await ApiService.post(url, callData, {}, token);
  } catch (error) {
    console.error('Error creating call:', error);
    throw error;
  }
};

/**
 * Update a call
 * @param {string} callId - Call ID
 * @param {Object} updateData - Update data
 * @param {string|null} token - Authentication token
 * @returns {Promise<Object>} - Updated call
 */
export const updateCall = async (callId, updateData, token = null) => {
  try {
    return await ApiService.put(`/calls/${callId}`, updateData, {}, token);
  } catch (error) {
    console.error('Error updating call:', error);
    throw error;
  }
};

/**
 * Delete a call
 * @param {string} callId - Call ID
 * @param {string|null} token - Authentication token
 * @returns {Promise<void>}
 */
export const deleteCall = async (callId, token = null) => {
  try {
    return await ApiService.delete(`/calls/${callId}`, {}, token);
  } catch (error) {
    console.error('Error deleting call:', error);
    throw error;
  }
};

/**
 * Get survey results for a specific call
 * @param {string} callId - Call ID
 * @param {string|null} token - Authentication token
 * @returns {Promise<Array>} - Survey results
 */
export const getCallSurveyResults = async (callId, token = null) => {
  try {
    return await ApiService.get(`/calls/${callId}/survey-results`, {}, token);
  } catch (error) {
    console.error('Error fetching call survey results:', error);
    throw error;
  }
};

/**
 * Get survey statistics summary
 * @param {string|null} token - Authentication token
 * @returns {Promise<Object>} - Survey statistics including type distribution
 */
export const getSurveyStats = async (token = null) => {
  try {
    return await ApiService.get('/surveys/stats/summary', {}, token);
  } catch (error) {
    console.error('Error fetching survey stats:', error);
    throw error;
  }
};

/**
 * Dashboard Analytics API functions
 */

/**
 * Get dashboard analytics data including sentiment trends and call volume
 * @param {string} period - Time period: 'today', 'week', 'month', 'all'
 * @param {string|null} token - Authentication token
 * @returns {Promise<Object>} - Dashboard analytics data
 */
export const getDashboardAnalytics = async (period = 'month', token = null) => {
  try {
    // Get calls data for analytics (limit to 100 per API constraints)
    const callsData = await getCalls({ limit: 100 }, token);
    const callStats = await getCallStats(period, token);
    const surveyStats = await getSurveyStats(token);
    
    return {
      calls: callsData,
      callStats,
      surveyStats
    };
  } catch (error) {
    console.error('Error fetching dashboard analytics:', error);
    throw error;
  }
};

/**
 * Get sentiment analysis data for dashboard charts
 * @param {string} period - Time period for analysis
 * @param {string|null} token - Authentication token
 * @returns {Promise<Object>} - Sentiment analysis data
 */
export const getSentimentAnalytics = async (period = 'month', token = null) => {
  try {
    // This would need to be implemented on the backend
    // For now, we'll parse the existing call data to extract sentiment
    const calls = await getCalls({ limit: 100 }, token);
    
    // Process calls to extract sentiment data
    const sentimentData = processSentimentData(calls, period);
    
    return sentimentData;
  } catch (error) {
    console.error('Error fetching sentiment analytics:', error);
    throw error;
  }
};

/**
 * Get call volume analytics for dashboard charts
 * @param {string} period - Time period for analysis
 * @param {string|null} token - Authentication token
 * @returns {Promise<Object>} - Call volume data
 */
export const getCallVolumeAnalytics = async (period = 'week', token = null) => {
  try {
    const calls = await getCalls({ limit: 100 }, token);
    
    // Process calls to get volume data by time period
    const volumeData = processCallVolumeData(calls, period);
    
    return volumeData;
  } catch (error) {
    console.error('Error fetching call volume analytics:', error);
    throw error;
  }
};

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
    console.warn('Calls data is not an array, using empty array');
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
    console.warn('Calls data is not an array, using empty array');
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
        // This might need adjustment based on your call data structure
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
export const initiateCall = async (callData, token = null) => {
  try {
    return await ApiService.post('/calls/initiate', callData, {}, token);
  } catch (error) {
    console.error('Error initiating call:', error);
    throw error;
  }
};

/**
 * Knowledge Base API functions
 */

/**
 * Get all documents with optional filtering
 * @param {Object} filters - Filter options (status, document_type, tag, skip, limit)
 * @param {string|null} token - Authentication token
 * @returns {Promise<Array>} - Array of documents
 */
export const getDocuments = async (filters = {}, token = null) => {
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
    console.error('Error fetching documents:', error);
    throw error;
  }
};

/**
 * Get a specific document by ID
 * @param {string} documentId - Document ID
 * @param {string|null} token - Authentication token
 * @returns {Promise<Object>} - Document data
 */
export const getDocumentById = async (documentId, token = null) => {
  try {
    return await ApiService.get(`/knowledge/${documentId}`, {}, token);
  } catch (error) {
    console.error(`Error fetching document ${documentId}:`, error);
    throw error;
  }
};

/**
 * Upload a new document
 * @param {FormData} formData - Form data containing file and metadata
 * @param {string|null} token - Authentication token
 * @returns {Promise<Object>} - Created document data
 */
export const uploadDocument = async (formData, token = null) => {
  try {
    const headers = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    // Don't set Content-Type for FormData, let browser set it with boundary
    
    const url = `${API_BASE_URL}/knowledge/upload`;
    console.log(`Making POST request to: ${url}`);
    
    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: formData,
    });
    
    console.log(`Response status: ${response.status} ${response.statusText}`);
    
    if (response.status === 401) {
      console.warn('Authentication token expired or invalid');
      throw new Error('Authentication failed. Please login again.');
    }
    
    let data;
    const contentType = response.headers.get('content-type');
    
    if (contentType && contentType.includes('application/json')) {
      data = await response.json();
    } else {
      const textResponse = await response.text();
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${textResponse || response.statusText}`);
      }
      return textResponse;
    }
    
    if (!response.ok) {
      const errorMessage = data?.detail || data?.error || data?.message || `HTTP ${response.status}: ${response.statusText}`;
      console.error(`Upload error (${response.status}):`, errorMessage);
      throw new Error(errorMessage);
    }
    
    console.log(`Document upload successful:`, data);
    return data;
  } catch (error) {
    console.error('Error uploading document:', error);
    throw error;
  }
};

/**
 * Delete a document
 * @param {string} documentId - Document ID
 * @param {string|null} token - Authentication token
 * @returns {Promise<void>}
 */
export const deleteDocument = async (documentId, token = null) => {
  try {
    return await ApiService.delete(`/knowledge/${documentId}`, {}, token);
  } catch (error) {
    console.error(`Error deleting document ${documentId}:`, error);
    throw error;
  }
};

/**
 * Update a document
 * @param {string} documentId - Document ID
 * @param {Object} updateData - Data to update
 * @param {string|null} token - Authentication token
 * @returns {Promise<Object>} - Updated document data
 */
export const updateDocument = async (documentId, updateData, token = null) => {
  try {
    return await ApiService.put(`/knowledge/${documentId}`, updateData, {}, token);
  } catch (error) {
    console.error(`Error updating document ${documentId}:`, error);
    throw error;
  }
};

/**
 * Search documents in knowledge base
 * @param {Object} searchQuery - Search query object {query, filters?, top_k?}
 * @param {string|null} token - Authentication token
 * @returns {Promise<Array>} - Array of search results
 */
export const searchDocuments = async (searchQuery, token = null) => {
  try {
    return await ApiService.post('/knowledge/search', searchQuery, {}, token);
  } catch (error) {
    console.error('Error searching documents:', error);
    throw error;
  }
};

/**
 * Create a knowledge base inquiry (no survey needed)
 * @param {Object} inquiryData - Inquiry data {phone_number, knowledge_base_id, product_context, send_immediately}
 * @param {string|null} token - Authentication token
 * @returns {Promise<Object>} - Created knowledge inquiry
 */
export const createKnowledgeInquiry = async (inquiryData, token = null) => {
  try {
    return await ApiService.post('/calls/knowledge-inquiry', inquiryData, {}, token);
  } catch (error) {
    console.error('Error creating knowledge inquiry:', error);
    throw error;
  }
};

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