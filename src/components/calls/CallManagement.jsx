import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { 
  PhoneCall, 
  PhoneIncoming, 
  PhoneOutgoing, 
  Calendar, 
  Clock, 
  User, 
  Play, 
  Pause,
  PlusCircle,
  Filter,
  Search,
  MoreHorizontal,
  FileText,
  Download,
  RefreshCw,
  StopCircle,
  X
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuItem, 
  DropdownMenuLabel, 
  DropdownMenuSeparator, 
  DropdownMenuTrigger 
} from '@/components/ui/dropdown-menu';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { 
  Dialog, 
  DialogContent, 
  DialogDescription, 
  DialogFooter, 
  DialogHeader, 
  DialogTitle
} from '@/components/ui/dialog';
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import ApiService from '@/services/api';

// Skeleton Components
const StatCardSkeleton = () => (
  <Card>
    <CardHeader className="pb-2">
      <Skeleton className="h-4 w-20" />
    </CardHeader>
    <CardContent>
      <Skeleton className="h-8 w-16 mb-2" />
      <Skeleton className="h-3 w-24" />
    </CardContent>
  </Card>
);

const CallItemSkeleton = () => (
  <div className="border-b p-4 flex items-center justify-between">
    <div className="flex items-center space-x-4">
      <Skeleton className="h-10 w-10 rounded-full" />
      <div className="space-y-2">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-3 w-48" />
      </div>
    </div>
    <div className="flex items-center space-x-3">
      <Skeleton className="h-4 w-16" />
      <Skeleton className="h-6 w-20 rounded-full" />
      <Skeleton className="h-8 w-8 rounded" />
    </div>
  </div>
);

const CampaignSkeleton = () => (
  <Card className="mb-4">
    <CardContent className="p-6">
      <div className="flex justify-between items-start mb-4">
        <div className="space-y-2">
          <Skeleton className="h-5 w-48" />
          <Skeleton className="h-4 w-64" />
        </div>
        <Skeleton className="h-6 w-16 rounded-full" />
      </div>
      
      <div className="mb-4">
        <div className="flex justify-between mb-1">
          <Skeleton className="h-3 w-16" />
          <Skeleton className="h-3 w-20" />
        </div>
        <Skeleton className="h-2 w-full rounded-full" />
      </div>
      
      <div className="grid grid-cols-3 gap-4 mb-4">
        {[1, 2, 3].map(i => (
          <div key={i} className="text-center p-2 bg-gray-50 rounded-md">
            <Skeleton className="h-6 w-8 mx-auto mb-1" />
            <Skeleton className="h-3 w-16 mx-auto" />
          </div>
        ))}
      </div>
      
      <div className="flex justify-end space-x-2">
        <Skeleton className="h-8 w-20" />
        <Skeleton className="h-8 w-16" />
      </div>
    </CardContent>
  </Card>
);

const QuickStatsSkeleton = () => (
  <Card>
    <CardHeader>
      <Skeleton className="h-5 w-24" />
    </CardHeader>
    <CardContent>
      <div className="space-y-4">
        <div>
          <Skeleton className="h-4 w-32 mb-1" />
          <Skeleton className="h-8 w-16" />
        </div>
        
        <Separator />
        
        <div>
          <Skeleton className="h-4 w-28 mb-1" />
          <div className="grid grid-cols-2 gap-2">
            {[1, 2].map(i => (
              <div key={i} className="bg-gray-50 p-3 rounded-md">
                <Skeleton className="h-5 w-6 mb-1" />
                <Skeleton className="h-3 w-16" />
              </div>
            ))}
          </div>
        </div>
        
        <Separator />
        
        <div>
          <Skeleton className="h-4 w-24 mb-1" />
          <div className="space-y-2">
            {[1, 2, 3].map(i => (
              <div key={i}>
                <div className="flex justify-between text-sm mb-1">
                  <Skeleton className="h-3 w-24" />
                  <Skeleton className="h-3 w-8" />
                </div>
                <Skeleton className="h-1 w-full rounded-full" />
              </div>
            ))}
          </div>
        </div>
      </div>
    </CardContent>
  </Card>
);

// Memoized Call Item Component
const CallItem = React.memo(({ call, type, onStartCall, onPauseCall, onResumeCall, onEndCall, onRetryCall, onCancelCall, onSendWhatsApp, onViewResults, onViewDetails }) => {
  return (
    <div className="border-b p-4 flex items-center justify-between">
      <div className="flex items-center space-x-4">
        {call.type === 'inbound' ? (
          <div className="bg-green-100 p-2 rounded-full">
            <PhoneIncoming size={18} className="text-green-600" />
          </div>
        ) : (
          <div className="bg-blue-100 p-2 rounded-full">
            <PhoneOutgoing size={18} className="text-blue-600" />
          </div>
        )}
        
        <div>
          <div className="font-medium">{call.phoneNumber}</div>
          <div className="text-sm text-gray-500 flex items-center space-x-2">
            <User size={14} />
            <span>{call.user}</span>
            <span>•</span>
            <span>{call.surveyType}</span>
            {call.metadata?.whatsapp_survey_sent && (
              <>
                <span>•</span>
                <span className="text-green-600">📱 WhatsApp Survey Sent</span>
              </>
            )}
            {call.metadata?.survey_completed && (
              <>
                <span>•</span>
                <span className="text-purple-600">✅ Survey Completed</span>
              </>
            )}
          </div>
        </div>
      </div>
      
      <div className="flex items-center space-x-3">
        {type === 'active' && (
          <>
            <div className="flex items-center">
              <Clock size={16} className="mr-1 text-gray-500" />
              <span>{call.duration}</span>
            </div>
            
            {call.callQuality && (
              <Badge variant="outline" className={
                call.callQuality === 'excellent' ? 'text-green-600 bg-green-50' :
                call.callQuality === 'good' ? 'text-blue-600 bg-blue-50' :
                'text-yellow-600 bg-yellow-50'
              }>
                {call.callQuality}
              </Badge>
            )}
            
            <Badge className={
              call.status === 'in-progress' ? 'bg-green-500' : 'bg-yellow-500'
            }>
              {call.status}
            </Badge>
            
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button size="sm" variant="ghost">
                  <MoreHorizontal size={16} />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>Call Actions</DropdownMenuLabel>
                <DropdownMenuSeparator />
                {call.status === 'in-progress' ? (
                  <DropdownMenuItem onClick={() => onPauseCall(call.id)}>
                    <Pause size={16} className="mr-2 text-yellow-500" />
                    Pause Call
                  </DropdownMenuItem>
                ) : (
                  <DropdownMenuItem onClick={() => onResumeCall(call.id)}>
                    <Play size={16} className="mr-2 text-green-500" />
                    Resume Call
                  </DropdownMenuItem>
                )}
                <DropdownMenuItem onClick={() => onEndCall(call.id)}>
                  <StopCircle size={16} className="mr-2 text-red-500" />
                  End Call
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => onSendWhatsApp(call.id)}>
                  <PhoneCall size={16} className="mr-2 text-green-500" />
                  Send WhatsApp Survey
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onViewResults(call.id)}>
                  <FileText size={16} className="mr-2 text-purple-500" />
                  View Survey Results
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onViewDetails(call.id)}>
                  <FileText size={16} className="mr-2" />
                  View Details
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </>
        )}
        
        {type === 'scheduled' && (
          <>
            <div className="flex items-center">
              <Calendar size={16} className="mr-1 text-gray-500" />
              <span className="whitespace-nowrap">{call.scheduledTime}</span>
            </div>
            
            {call.priority && (
              <Badge variant="outline" className={
                call.priority === 'high' ? 'text-red-600 bg-red-50' :
                call.priority === 'normal' ? 'text-blue-600 bg-blue-50' :
                'text-gray-600 bg-gray-50'
              }>
                {call.priority}
              </Badge>
            )}
            
            <Badge className="bg-blue-500">Scheduled</Badge>
            
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button size="sm" variant="ghost">
                  <MoreHorizontal size={16} />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>Call Actions</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => onStartCall(call.id)}>
                  <Play size={16} className="mr-2 text-green-500" />
                  Start Call Now
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => onSendWhatsApp(call.id)}>
                  <PhoneCall size={16} className="mr-2 text-green-500" />
                  Send WhatsApp Survey
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onViewResults(call.id)}>
                  <FileText size={16} className="mr-2 text-purple-500" />
                  View Survey Results
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onViewDetails(call.id)}>
                  <FileText size={16} className="mr-2" />
                  View Details
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </>
        )}
        
        {type === 'completed' && (
          <>
            <div className="flex items-center">
              <Clock size={16} className="mr-1 text-gray-500" />
              <span>{call.duration}</span>
            </div>
            
            {call.sentiment && (
              <Badge variant="outline" className={
                call.sentiment === 'positive' ? 'text-green-600 bg-green-50' :
                call.sentiment === 'neutral' ? 'text-blue-600 bg-blue-50' :
                'text-red-600 bg-red-50'
              }>
                {call.sentiment}
              </Badge>
            )}
            
            {call.success ? (
              <Badge className="bg-green-500">Completed</Badge>
            ) : (
              <Badge className="bg-yellow-500">Partial</Badge>
            )}
            
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button size="sm" variant="ghost">
                  <MoreHorizontal size={16} />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>Call Actions</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => onViewResults(call.id)}>
                  <FileText size={16} className="mr-2 text-purple-500" />
                  View Survey Results
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onViewDetails(call.id)}>
                  <FileText size={16} className="mr-2" />
                  View Details
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => showToast("Download Recording", "Download feature coming soon")}>
                  <Download size={16} className="mr-2" />
                  Download Recording
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </>
        )}
        
        {type === 'failed' && (
          <>
            <div className="text-sm text-red-500">{call.failureReason}</div>
            
            <Badge variant="outline" className="text-gray-600 bg-gray-50">
              {call.retryAttempts}/{call.maxRetries} attempts
            </Badge>
            
            <Badge className="bg-red-500">Failed</Badge>
            
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button size="sm" variant="ghost">
                  <MoreHorizontal size={16} />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>Call Actions</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => onRetryCall(call.id)}>
                  <Play size={16} className="mr-2 text-green-500" />
                  Retry Call
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => onSendWhatsApp(call.id)}>
                  <PhoneCall size={16} className="mr-2 text-green-500" />
                  Send WhatsApp Survey
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onViewResults(call.id)}>
                  <FileText size={16} className="mr-2 text-purple-500" />
                  View Survey Results
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onViewDetails(call.id)}>
                  <FileText size={16} className="mr-2" />
                  View Details
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </>
        )}
      </div>
    </div>
  );
});

CallItem.displayName = 'CallItem';

// Memoized Campaign Item Component
const CampaignItem = React.memo(({ campaign }) => {
  return (
    <Card className="mb-4">
      <CardContent className="p-6">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h3 className="text-lg font-medium">{campaign.name}</h3>
            <p className="text-sm text-gray-500">{campaign.description}</p>
          </div>
          <Badge className={
            campaign.status === 'active' ? 'bg-green-500' : 
            campaign.status === 'scheduled' ? 'bg-blue-500' : 
            campaign.status === 'completed' ? 'bg-purple-500' : 'bg-gray-500'
          }>
            {campaign.status}
          </Badge>
        </div>
        
        <div className="mb-4">
          <div className="flex justify-between mb-1">
            <span className="text-sm text-gray-500">Progress</span>
            <span className="text-sm font-medium">{campaign.completedCalls}/{campaign.totalCalls} calls</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-blue-600 h-2 rounded-full" 
              style={{ width: `${campaign.progress}%` }}
            ></div>
          </div>
        </div>
        
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div className="text-center p-2 bg-gray-50 rounded-md">
            <div className="text-lg font-medium">{campaign.totalCalls}</div>
            <div className="text-xs text-gray-500">Total Calls</div>
          </div>
          <div className="text-center p-2 bg-gray-50 rounded-md">
            <div className="text-lg font-medium">{campaign.completedCalls}</div>
            <div className="text-xs text-gray-500">Completed</div>
          </div>
          <div className="text-center p-2 bg-gray-50 rounded-md">
            <div className="text-lg font-medium">{campaign.successRate}%</div>
            <div className="text-xs text-gray-500">Success Rate</div>
          </div>
        </div>
        
        <div className="flex justify-end space-x-2">
          <Button variant="outline" size="sm">View Details</Button>
          {campaign.status === 'active' && (
            <Button variant="outline" size="sm" className="text-yellow-600">Pause</Button>
          )}
          {campaign.status === 'scheduled' && (
            <Button size="sm" className="bg-green-500">Start Now</Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
});

CampaignItem.displayName = 'CampaignItem';

const CallManagement = () => {
  const { getToken } = useAuth();
  
  // State management
  const [activeTab, setActiveTab] = useState('dashboard');
  const [calls, setCalls] = useState({
    active: [],
    scheduled: [],
    completed: [],
    failed: []
  });
  const [campaigns, setCampaigns] = useState([]);
  const [surveys, setSurveys] = useState([]);
  const [knowledgeBase, setKnowledgeBase] = useState([]);
  const [callStats, setCallStats] = useState({
    total: 0,
    active: 0,
    completed: 0,
    scheduled: 0,
    failed: 0,
    avgDuration: 0
  });
  const [surveyStats, setSurveyStats] = useState({
    survey_type_distribution: {
      "Customer Satisfaction": 0,
      "Product Feedback": 0,
      "Technical Support": 0
    }
  });
  
  // Loading states
  const [isLoading, setIsLoading] = useState(true);
  const [isStatsLoading, setIsStatsLoading] = useState(true);
  const [isCallsLoading, setIsCallsLoading] = useState(true);
  const [isSurveysLoading, setIsSurveysLoading] = useState(true);
  const [isKnowledgeLoading, setIsKnowledgeLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  
  const [isCreatingCampaign, setIsCreatingCampaign] = useState(false);
  const [isSchedulingCall, setIsSchedulingCall] = useState(false);
  const [isCallDetailsOpen, setIsCallDetailsOpen] = useState(false);
  const [selectedCallDetails, setSelectedCallDetails] = useState(null);
  const [filterValues, setFilterValues] = useState({
    surveyType: 'all',
    dateRange: 'all',
    search: ''
  });
  const [newCall, setNewCall] = useState({
    phoneNumber: '',
    name: '',
    surveyId: '',
    knowledgeBaseId: 'none',
    scheduledDate: '',
    scheduledTime: '',
    notes: '',
    priority: 'normal',
    sendWhatsAppSurvey: false,
    knowledgeBaseOnly: false
  });
  const [toast, setToast] = useState({ 
    visible: false, 
    title: '', 
    description: '', 
    type: 'default' 
  });
  const [error, setError] = useState(null);

  // Memoized helper function to make authenticated API calls
  const makeAuthenticatedRequest = useCallback(async (endpoint, options = {}) => {
    try {
      let token = null;
      
      // Only get token if user is signed in (not in debug mode)
      try {
        token = await getToken();
      } catch (error) {
        // In debug mode or when not authenticated, proceed without token
      }
      
      if (options.method && ['POST', 'PUT', 'DELETE'].includes(options.method)) {
        // For mutating operations, use ApiService methods with token
        switch (options.method) {
          case 'POST':
            return await ApiService.post(endpoint, options.body ? JSON.parse(options.body) : {}, {}, token);
          case 'PUT':
            return await ApiService.put(endpoint, options.body ? JSON.parse(options.body) : {}, {}, token);
          case 'DELETE':
            return await ApiService.delete(endpoint, {}, token);
        }
      } else {
        // For GET requests, use ApiService.get with token
        return await ApiService.get(endpoint, {}, token);
      }
    } catch (error) {
      throw error;
    }
  }, [getToken]);
  
  // Memoized toast notification function
  const showToast = useCallback((title, description, type = 'default') => {
    setToast({ visible: true, title, description, type });
    setTimeout(() => {
      setToast({ visible: false, title: '', description: '', type: 'default' });
    }, 3000);
  }, []);

  // Memoized format duration function
  const formatDuration = useCallback((seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }, []);

  // Memoized transform call data function
  const transformCallData = useCallback((apiCall) => {
    return {
      id: apiCall.id,
      type: 'outbound', // Most calls are outbound in this system
      phoneNumber: apiCall.phone_number,
      status: apiCall.status,
      duration: apiCall.duration_seconds ? formatDuration(apiCall.duration_seconds) : '00:00',
      user: apiCall.metadata?.name || 'Unknown',
      surveyType: apiCall.survey_id || 'General Survey',
      callQuality: 'good', // Default value, can be enhanced later
      scheduledTime: apiCall.scheduled_time || apiCall.created_at,
      completedTime: apiCall.ended_at,
      success: apiCall.status === 'completed',
      sentiment: apiCall.metadata?.sentiment || 'neutral',
      failureReason: apiCall.metadata?.failure_reason || 'Unknown',
      retryAttempts: apiCall.metadata?.retry_attempts || 0,
      maxRetries: 3,
      priority: apiCall.metadata?.priority || 'normal',
      notes: apiCall.metadata?.notes || '',
      twilio_call_sid: apiCall.twilio_call_sid
    };
  }, [formatDuration]);
  
  // Optimized fetch surveys function
  const fetchSurveys = useCallback(async () => {
    if (!getToken) return;
    
    try {
      const surveysResponse = await makeAuthenticatedRequest('/surveys?limit=50');
      setSurveys(surveysResponse || []);
    } catch (error) {
      showToast("Warning", "Failed to load surveys. You may need to create surveys first.", "error");
      setSurveys([]);
    } finally {
      setIsSurveysLoading(false);
    }
  }, [makeAuthenticatedRequest, getToken, showToast]);

  // Optimized fetch knowledge base function
  const fetchKnowledgeBase = useCallback(async () => {
    if (!getToken) return;
    
    try {
      // Use the correct endpoint - it's /api/knowledge/ not /knowledge
      const knowledgeResponse = await makeAuthenticatedRequest('/knowledge');
      
      // Transform the response to ensure we have the right field names
      const transformedDocs = knowledgeResponse.map(doc => ({
        id: doc.id,
        title: doc.name, // API returns 'name' field, but we use 'title' in UI
        name: doc.name,
        filename: doc.name,
        description: doc.description,
        status: doc.status
      }));
      
      setKnowledgeBase(transformedDocs || []);
    } catch (error) {
      showToast("Warning", "Failed to load knowledge base. You may need to upload documents first.", "error");
      setKnowledgeBase([]);
    } finally {
      setIsKnowledgeLoading(false);
    }
  }, [makeAuthenticatedRequest, getToken, showToast]);

  // Optimized fetch call data with parallel loading
  const fetchCallData = useCallback(async (showRefreshingState = false) => {
    if (!getToken) return;
    
    if (showRefreshingState) {
      setIsRefreshing(true);
    } else {
      setIsCallsLoading(true);
      setIsStatsLoading(true);
    }
    
    setError(null);
    const startTime = Date.now();
    
    try {
      // Fetch call stats and survey stats in parallel for better performance
      const [callsResponse, statsResponse, surveyStatsResponse] = await Promise.all([
        makeAuthenticatedRequest('/calls/', { 
          method: 'GET',
          params: { limit: 100 }
        }),
        makeAuthenticatedRequest('/calls/stats/summary'),
        makeAuthenticatedRequest('/surveys/stats/summary')
      ]);

      // Transform call data
      const transformedCalls = {
        active: [],
        scheduled: [],
        completed: [],
        failed: []
      };

      if (callsResponse && Array.isArray(callsResponse)) {
        callsResponse.forEach(apiCall => {
          const transformedCall = transformCallData(apiCall);
          
          if (transformedCall.status === 'in-progress') {
            transformedCalls.active.push(transformedCall);
          } else if (transformedCall.status === 'scheduled') {
            transformedCalls.scheduled.push(transformedCall);
          } else if (transformedCall.status === 'completed') {
            transformedCalls.completed.push(transformedCall);
          } else if (['failed', 'cancelled'].includes(transformedCall.status)) {
            transformedCalls.failed.push(transformedCall);
          }
        });
      }

      setCalls(transformedCalls);

      // Use real API stats instead of calculating from call data
      const realStats = {
        total: statsResponse.total_calls || 0,
        active: statsResponse.in_progress_calls || 0,
        completed: statsResponse.completed_calls || 0,
        scheduled: statsResponse.scheduled_calls || 0,
        failed: (statsResponse.failed_calls || 0) + (statsResponse.cancelled_calls || 0),
        avgDuration: statsResponse.average_duration_seconds || 0
      };

      setCallStats(realStats);
      setSurveyStats(surveyStatsResponse);
      
      // Mock campaigns for now (can be implemented later)
      setCampaigns([
        {
          id: 'camp-001',
          name: 'Customer Feedback Campaign',
          description: 'Collecting feedback from recent customers',
          status: 'active',
          totalCalls: realStats.total,
          completedCalls: realStats.completed,
          successRate: realStats.total > 0 ? 
            (realStats.completed / realStats.total * 100) : 0,
          progress: realStats.total > 0 ? 
            (realStats.completed / realStats.total * 100) : 0
        }
      ]);
      
    } catch (error) {
      setError('Failed to load call data. Please try again.');
      showToast(
        "Error", 
        "Failed to load call data. Please try again.", 
        "error"
      );
    } finally {
      const elapsedTime = Date.now() - startTime;
      
      // Ensure minimum loading time for smooth UX
      const remainingTime = Math.max(0, 300 - elapsedTime);
      setTimeout(() => {
        setIsCallsLoading(false);
        setIsStatsLoading(false);
        setIsRefreshing(false);
      }, remainingTime);
    }
  }, [makeAuthenticatedRequest, getToken, transformCallData, showToast]);

  // Memoized filtered data calculation
  const getFilteredData = useMemo(() => {
    return (data) => {
      return data.filter(item => {
        // Search filter
        const searchMatch = !filterValues.search || 
          (item.phoneNumber && item.phoneNumber.includes(filterValues.search)) ||
          (item.user && item.user.toLowerCase().includes(filterValues.search.toLowerCase()));
        
        // Survey type filter
        const surveyMatch = filterValues.surveyType === 'all' || item.surveyType === filterValues.surveyType;
        
        // Date range filter
        let dateMatch = true;
        
        return searchMatch && surveyMatch && dateMatch;
      });
    };
  }, [filterValues.search, filterValues.surveyType]);

  // Initial data fetch with parallel loading
  useEffect(() => {
    const initializeData = async () => {
      setIsLoading(true);
      
      // Load critical data first (calls and stats)
      await fetchCallData(false);
      
      // Load secondary data in parallel
      await Promise.all([
        fetchSurveys(),
        fetchKnowledgeBase()
      ]);
    };
    
    initializeData();
  }, [fetchCallData, fetchSurveys, fetchKnowledgeBase]);

  // Debounced refresh when filters change
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      if (!isLoading) { // Only refresh if initial load is complete
        fetchCallData(true);
      }
    }, 500); // Debounce filter changes
    
    return () => clearTimeout(timeoutId);
  }, [filterValues.surveyType, filterValues.dateRange, filterValues.search, fetchCallData, isLoading]);

  // Memoized format avg duration function
  const formatAvgDuration = useCallback((seconds) => {
    // Handle null, undefined, NaN, or non-numeric values
    if (!seconds || isNaN(seconds) || seconds <= 0) {
      return '0:00';
    }
    
    // Ensure we have a number and round it
    const totalSeconds = Math.round(Number(seconds));
    
    // Calculate minutes and remaining seconds
    const minutes = Math.floor(totalSeconds / 60);
    const remainingSeconds = totalSeconds % 60;
    
    // Format as MM:SS
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  }, []);

  // Format date for display
  const formatDate = useCallback((dateString) => {
    if (!dateString) return "";
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: 'numeric'
    }).format(date);
  }, []);

  // Memoized call action handlers
  const handleStartCall = useCallback(async (callId) => {
    try {
      await makeAuthenticatedRequest(`/calls/${callId}/start`, { method: 'POST' });
      showToast("Success", "Call started successfully", "success");
      await fetchCallData(true); // Refresh data
    } catch (error) {
      showToast("Error", "Failed to start call. Please try again.", "error");
    }
  }, [makeAuthenticatedRequest, showToast, fetchCallData]);

  const handlePauseCall = useCallback(async (callId) => {
    try {
      // Note: In reality, live phone calls can't be "paused" 
      // This would typically end the call and mark it as paused for retry later
      await makeAuthenticatedRequest(`/calls/${callId}`, { 
        method: 'PUT',
        body: JSON.stringify({ status: 'paused' })
      });
      showToast("Call Paused", "Call has been paused and can be resumed later", "success");
      await fetchCallData(true); // Refresh data
    } catch (error) {
      if (error.response?.status === 400) {
        showToast("Cannot Pause", "This call cannot be paused in its current state", "error");
      } else {
        showToast("Error", "Failed to pause call. Please try again.", "error");
      }
    }
  }, [makeAuthenticatedRequest, showToast, fetchCallData]);

  const handleResumeCall = useCallback(async (callId) => {
    try {
      await makeAuthenticatedRequest(`/calls/${callId}`, { 
        method: 'PUT',
        body: JSON.stringify({ status: 'in-progress' })
      });
      showToast("Call Resumed", "Call has been resumed successfully", "success");
      await fetchCallData(true); // Refresh data
    } catch (error) {
      if (error.response?.status === 400) {
        showToast("Cannot Resume", "This call cannot be resumed in its current state", "error");
      } else {
        showToast("Error", "Failed to resume call. Please try again.", "error");
      }
    }
  }, [makeAuthenticatedRequest, showToast, fetchCallData]);

  const handleEndCall = useCallback(async (callId) => {
    try {
      await makeAuthenticatedRequest(`/calls/${callId}`, { 
        method: 'PUT',
        body: JSON.stringify({ status: 'completed' })
      });
      showToast("Success", "Call ended successfully", "success");
      await fetchCallData(true); // Refresh data
    } catch (error) {
      // Provide more specific error messages
      if (error.message.includes('Network error')) {
        showToast("Network Error", "Unable to connect to server. Please check your connection.", "error");
      } else if (error.message.includes('Authentication failed')) {
        showToast("Authentication Error", "Please login again to continue.", "error");
      } else if (error.message.includes('HTTP 400')) {
        showToast("Invalid Request", "This call cannot be ended in its current state.", "error");
      } else if (error.message.includes('HTTP 404')) {
        showToast("Call Not Found", "The call could not be found. It may have been deleted.", "error");
      } else if (error.message.includes('HTTP 500')) {
        showToast("Server Error", "Server error occurred. Please try again later.", "error");
      } else {
        showToast("Error", `Failed to end call: ${error.message}`, "error");
      }
    }
  }, [makeAuthenticatedRequest, showToast, fetchCallData]);

  const handleRetryCall = useCallback(async (callId) => {
    try {
      // First update the status to scheduled
      await makeAuthenticatedRequest(`/calls/${callId}`, { 
        method: 'PUT',
        body: JSON.stringify({ status: 'scheduled' })
      });
      // Then start the call
      await makeAuthenticatedRequest(`/calls/${callId}/start`, { method: 'POST' });
      showToast("Success", "Call retry initiated successfully", "success");
      await fetchCallData(true); // Refresh data
    } catch (error) {
      showToast("Error", "Failed to retry call. Please try again.", "error");
    }
  }, [makeAuthenticatedRequest, showToast, fetchCallData]);

  const handleCancelCall = useCallback(async (callId) => {
    try {
      await makeAuthenticatedRequest(`/calls/${callId}/cancel`, { method: 'POST' });
      showToast("Success", "Call cancelled successfully", "success");
      await fetchCallData(true); // Refresh data
    } catch (error) {
      showToast("Error", "Failed to cancel call. Please try again.", "error");
    }
  }, [makeAuthenticatedRequest, showToast, fetchCallData]);

  const handleSendWhatsAppSurvey = useCallback(async (callId) => {
    try {
      await makeAuthenticatedRequest(`/calls/${callId}/send-whatsapp-survey`, { method: 'POST' });
      showToast("WhatsApp Survey Sent", "Survey has been sent via WhatsApp successfully", "success");
      await fetchCallData(true); // Refresh data
    } catch (error) {
      showToast("Error", "Failed to send WhatsApp survey. Please try again.", "error");
    }
  }, [makeAuthenticatedRequest, showToast, fetchCallData]);

  const handleViewSurveyResults = useCallback(async (callId) => {
    try {
      const results = await makeAuthenticatedRequest(`/calls/${callId}/survey-results`);
      
      if (results && results.length > 0) {
        // Show results in a dialog or navigate to results page
        showToast("Survey Results", `Found ${results.length} survey result(s)`, "success");
        // TODO: Open survey results dialog or navigate to results page
      } else {
        showToast("No Results", "No survey results found for this call", "info");
      }
    } catch (error) {
      showToast("Error", "Failed to fetch survey results. Please try again.", "error");
    }
  }, [makeAuthenticatedRequest, showToast]);

  const handleViewCallDetails = useCallback(async (callId) => {
    try {
      const callDetails = await makeAuthenticatedRequest(`/calls/${callId}`);
      
      // Transform the API response to match the component's expected format
      const transformedDetails = {
        id: callDetails.id,
        phoneNumber: callDetails.phone_number,
        user: callDetails.metadata?.name || 'Unknown Contact',
        type: 'outbound', // Most calls in this system are outbound
        surveyType: callDetails.survey_id || 'General Survey',
        status: callDetails.status,
        duration: callDetails.duration_seconds ? formatDuration(callDetails.duration_seconds) : 'N/A',
        scheduledTime: callDetails.scheduled_time ? formatDate(callDetails.scheduled_time) : 'N/A',
        completedTime: callDetails.ended_at ? formatDate(callDetails.ended_at) : 'N/A',
        createdTime: callDetails.created_at ? formatDate(callDetails.created_at) : 'N/A',
        callQuality: callDetails.metadata?.call_quality || 'N/A',
        sentiment: callDetails.metadata?.sentiment || 'N/A',
        failureReason: callDetails.metadata?.failure_reason || (callDetails.status === 'failed' ? 'Unknown error' : null),
        retryAttempts: callDetails.metadata?.retry_attempts || 0,
        maxRetries: 3,
        priority: callDetails.metadata?.priority || 'normal',
        notes: callDetails.metadata?.notes || 'No notes available',
        twilioCallSid: callDetails.twilio_call_sid || 'N/A',
        success: callDetails.status === 'completed',
        // Additional details for comprehensive view
        recordingUrl: callDetails.metadata?.recording_url || null,
        callbackUrl: callDetails.metadata?.callback_url || null,
        dialedAt: callDetails.metadata?.dialed_at ? formatDate(callDetails.metadata.dialed_at) : null,
        answeredAt: callDetails.metadata?.answered_at ? formatDate(callDetails.metadata.answered_at) : null,
        hangupReason: callDetails.metadata?.hangup_reason || null,
        surveyResponses: callDetails.metadata?.survey_responses || null,
        callCost: callDetails.metadata?.call_cost || null,
        fromNumber: callDetails.metadata?.from_number || 'System',
        toNumber: callDetails.phone_number,
        direction: callDetails.metadata?.direction || 'outbound',
        callSid: callDetails.twilio_call_sid
      };
      
      setSelectedCallDetails(transformedDetails);
      setIsCallDetailsOpen(true);
    } catch (error) {
      showToast("Error", "Failed to load call details. Please try again.", "error");
    }
  }, [makeAuthenticatedRequest, showToast, formatDuration, formatDate]);

  // Handle scheduling a new call
  const handleScheduleCall = useCallback(async () => {
    try {
      // Create a new call object
      const callData = {
        phone_number: newCall.phoneNumber,
        scheduled_time: `${newCall.scheduledDate}T${newCall.scheduledTime}:00`,
        metadata: {
          name: newCall.name,
          priority: newCall.priority,
          notes: newCall.notes,
          ...(newCall.knowledgeBaseId !== 'none' && { knowledge_base_id: newCall.knowledgeBaseId })
        }
      };

      // Add survey_id only if it's not a knowledge base only call
      if (!newCall.knowledgeBaseOnly) {
        callData.survey_id = newCall.surveyId;
      }

      // Create the call via API
      if (newCall.knowledgeBaseOnly) {
        // Use the new knowledge base inquiry endpoint
        const inquiryData = {
          phone_number: newCall.phoneNumber,
          knowledge_base_id: newCall.knowledgeBaseId,
          product_context: newCall.notes || "General product inquiry",
          send_immediately: newCall.sendWhatsAppSurvey
        };
        await makeAuthenticatedRequest('/calls/knowledge-inquiry', {
          method: 'POST',
          body: JSON.stringify(inquiryData)
        });
      } else {
        // Traditional survey-based call
        const endpoint = newCall.sendWhatsAppSurvey 
          ? `/calls?send_whatsapp_survey=true` 
          : '/calls';
        
        await makeAuthenticatedRequest(endpoint, {
          method: 'POST',
          body: JSON.stringify(callData)
        });
      }
      
      // Refresh the data to show the new call
      await fetchCallData(true);
    
      // Show success message
      let successMessage;
      if (newCall.knowledgeBaseOnly) {
        successMessage = newCall.sendWhatsAppSurvey 
          ? `Knowledge base inquiry sent immediately to ${newCall.phoneNumber}`
          : `Knowledge base inquiry scheduled for ${newCall.phoneNumber}`;
      } else {
        successMessage = newCall.sendWhatsAppSurvey 
          ? `Call scheduled and WhatsApp survey sent to ${newCall.phoneNumber}`
          : `Call to ${newCall.phoneNumber} has been scheduled`;
      }
    
      showToast(
        "Call Scheduled", 
        successMessage, 
        "success"
      );
    
      // Reset form and close dialog
      setNewCall({
        phoneNumber: '',
        name: '',
        surveyId: '',
        knowledgeBaseId: 'none',
        scheduledDate: '',
        scheduledTime: '',
        notes: '',
        priority: 'normal',
        sendWhatsAppSurvey: false,
        knowledgeBaseOnly: false
      });
      setIsSchedulingCall(false);
    } catch (error) {
      showToast(
        "Error", 
        "Failed to schedule call. Please try again.", 
        "error"
      );
    }
  }, [newCall, makeAuthenticatedRequest, fetchCallData, showToast]);

  return (
    <div className="mx-auto max-w-7xl p-4 space-y-6">
      {/* Custom Toast Notification */}
      {toast.visible && (
        <div className={`fixed top-4 right-4 p-4 rounded-md shadow-md z-50 max-w-md 
          ${toast.type === 'error' ? 'bg-red-100 border-red-500' : 
            toast.type === 'success' ? 'bg-green-100 border-green-500' : 
            'bg-blue-100 border-blue-500'}`}>
          <div className="flex items-start">
            <div className="ml-3">
              <p className="text-sm font-medium">{toast.title}</p>
              <p className="mt-1 text-sm text-gray-500">{toast.description}</p>
            </div>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2">
              <div className="text-red-600">
                <X size={20} />
              </div>
              <div>
                <h3 className="text-sm font-medium text-red-800">Error Loading Data</h3>
                <p className="text-sm text-red-600 mt-1">{error}</p>
              </div>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={fetchCallData}
                className="ml-auto"
              >
                Try Again
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
      
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Call Management</h1>
        <div className="flex space-x-2">
          <Button 
            variant="outline" 
            onClick={fetchCallData} 
            disabled={isRefreshing}
            className="flex items-center gap-2"
          >
            <RefreshCw size={16} className={isRefreshing ? "animate-spin" : ""} />
            Refresh
          </Button>
          
          <Button onClick={() => setIsSchedulingCall(true)} className="bg-blue-600 flex items-center gap-2">
            <PlusCircle size={16} />
            Schedule Call
          </Button>
          
          <Button onClick={() => setIsCreatingCampaign(true)} className="bg-blue-600 flex items-center gap-2">
            <PlusCircle size={16} />
            New Campaign
          </Button>
        </div>
      </div>

      <Tabs defaultValue="dashboard" onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="grid grid-cols-5 w-full">
          <TabsTrigger value="dashboard">Dashboard</TabsTrigger>
          <TabsTrigger value="active">Active Calls</TabsTrigger>
          <TabsTrigger value="scheduled">Scheduled</TabsTrigger>
          <TabsTrigger value="completed">Completed</TabsTrigger>
          <TabsTrigger value="failed">Failed</TabsTrigger>
        </TabsList>

        {/* Dashboard Tab */}
        <TabsContent value="dashboard" className="space-y-4">
          {/* Stats Cards */}
          <div className="grid grid-cols-3 md:grid-cols-6 gap-4">
            {isStatsLoading ? (
              // Show skeleton for stats cards
              <>
                <div className="col-span-3 md:col-span-2">
                  <StatCardSkeleton />
                </div>
                {[1, 2, 3, 4].map(i => (
                  <StatCardSkeleton key={i} />
                ))}
              </>
            ) : (
              <>
                <Card className="col-span-3 md:col-span-2">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base text-gray-500">Total Calls</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold">{callStats.total}</div>
                    <p className="text-xs text-gray-500 mt-2">
                      Across {campaigns.length} campaigns
                    </p>
                  </CardContent>
                </Card>
                
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base text-gray-500">Active</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold text-green-600">{callStats.active}</div>
                  </CardContent>
                </Card>
                
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base text-gray-500">Scheduled</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold text-blue-600">{callStats.scheduled}</div>
                  </CardContent>
                </Card>
                
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base text-gray-500">Completed</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold text-purple-600">{callStats.completed}</div>
                  </CardContent>
                </Card>
                
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base text-gray-500">Failed</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold text-red-600">{callStats.failed}</div>
                  </CardContent>
                </Card>
              </>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Active Campaigns */}
            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle>Active Campaigns</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {isLoading ? (
                    // Show skeleton for campaigns
                    <>
                      <CampaignSkeleton />
                      <CampaignSkeleton />
                    </>
                  ) : (
                    <>
                      {campaigns.filter(c => c.status === 'active').map(campaign => (
                        <CampaignItem key={campaign.id} campaign={campaign} />
                      ))}
                      
                      {campaigns.filter(c => c.status === 'active').length === 0 && (
                        <div className="text-center py-8 text-gray-500">
                          No active campaigns. Create a new campaign to get started.
                        </div>
                      )}
                    </>
                  )}
                </div>
              </CardContent>
            </Card>
            
            {/* Quick Stats */}
            <Card>
              <CardHeader>
                <CardTitle>Quick Stats</CardTitle>
              </CardHeader>
              <CardContent>
                {isStatsLoading ? (
                  <QuickStatsSkeleton />
                ) : (
                  <div className="space-y-4">
                    <div>
                      <h3 className="text-sm font-medium text-gray-500 mb-1">Avg. Call Duration</h3>
                      <p className="text-2xl font-bold">{formatAvgDuration(callStats.avgDuration)}</p>
                    </div>
                    
                    <Separator />
                    
                    <div>
                      <h3 className="text-sm font-medium text-gray-500 mb-1">Today's Activity</h3>
                      <div className="grid grid-cols-2 gap-2">
                        <div className="bg-gray-50 p-3 rounded-md">
                          <p className="text-lg font-medium">{calls.active.length}</p>
                          <p className="text-xs text-gray-500">Active Now</p>
                        </div>
                        <div className="bg-gray-50 p-3 rounded-md">
                          <p className="text-lg font-medium">{calls.scheduled.filter(c => c.scheduledTime.includes('2025-04-08')).length}</p>
                          <p className="text-xs text-gray-500">Today's Schedule</p>
                        </div>
                      </div>
                    </div>
                    
                    <Separator />
                    
                    <div>
                      <h3 className="text-sm font-medium text-gray-500 mb-1">Survey Types</h3>
                      <div className="space-y-2">
                        {Object.entries(surveyStats.survey_type_distribution).map(([type, data]) => (
                          <div key={type}>
                            <div className="flex justify-between text-sm">
                              <span>{type}</span>
                              <span className="font-medium">{data}%</span>
                            </div>
                            <div className="w-full bg-gray-200 rounded-full h-1">
                              <div className="bg-blue-600 h-1 rounded-full" style={{ width: `${data}%` }}></div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Active Calls Tab */}
        <TabsContent value="active">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Active Calls</CardTitle>
              <div className="flex items-center space-x-2">
                <Button variant="outline" size="sm" onClick={() => fetchCallData(true)} disabled={isRefreshing}>
                  <RefreshCw size={14} className={`mr-2 ${isRefreshing ? "animate-spin" : ""}`} />
                  Refresh
                </Button>
              </div>
            </CardHeader>
            
            <CardContent>
              {!isCallsLoading && (
                <div className="mb-4">
                  <p className="text-sm text-gray-500">
                    {calls.active.length} active calls in progress
                  </p>
                </div>
              )}
              
              <div className="rounded-md border">
                {isCallsLoading ? (
                  // Show skeleton for active calls
                  <>
                    {[1, 2, 3].map(i => <CallItemSkeleton key={i} />)}
                  </>
                ) : calls.active.length > 0 ? (
                  calls.active.map(call => (
                    <CallItem key={call.id} call={call} type="active" onStartCall={handleStartCall} onPauseCall={handlePauseCall} onResumeCall={handleResumeCall} onEndCall={handleEndCall} onRetryCall={handleRetryCall} onCancelCall={handleCancelCall} onSendWhatsApp={handleSendWhatsAppSurvey} onViewResults={handleViewSurveyResults} onViewDetails={handleViewCallDetails} />
                  ))
                ) : (
                  <div className="p-8 text-center text-gray-500">
                    No active calls at the moment.
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Scheduled Calls Tab */}
        <TabsContent value="scheduled">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Scheduled Calls</CardTitle>
              <div className="flex items-center space-x-2">
                <Input
                  placeholder="Search..."
                  className="w-64"
                  value={filterValues.search}
                  onChange={(e) => setFilterValues({...filterValues, search: e.target.value})}
                />
                <Select 
                  value={filterValues.surveyType} 
                  onValueChange={(value) => setFilterValues({...filterValues, surveyType: value})}
                >
                  <SelectTrigger className="w-40">
                    <SelectValue placeholder="Survey Type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Surveys</SelectItem>
                    <SelectItem value="Customer Satisfaction">Customer Satisfaction</SelectItem>
                    <SelectItem value="Product Feedback">Product Feedback</SelectItem>
                    <SelectItem value="Technical Support">Technical Support</SelectItem>
                  </SelectContent>
                </Select>
                <Button size="sm" onClick={() => fetchCallData(true)} disabled={isRefreshing}>
                  <RefreshCw size={14} className={`mr-2 ${isRefreshing ? "animate-spin" : ""}`} />
                  Refresh
                </Button>
              </div>
            </CardHeader>
            
            <CardContent>
              {!isCallsLoading && (
                <div className="flex justify-between items-center mb-4">
                  <p className="text-sm text-gray-500">
                    {calls.scheduled.length} scheduled calls
                  </p>
                  <Button 
                    size="sm" 
                    className="flex items-center gap-2"
                    onClick={() => setIsSchedulingCall(true)}
                  >
                    <PlusCircle size={16} />
                    Schedule Call
                  </Button>
                </div>
              )}
              
              <div className="rounded-md border">
                {isCallsLoading ? (
                  // Show skeleton for scheduled calls
                  <>
                    {[1, 2, 3, 4, 5].map(i => <CallItemSkeleton key={i} />)}
                  </>
                ) : getFilteredData(calls.scheduled).length > 0 ? (
                  getFilteredData(calls.scheduled).map(call => (
                    <CallItem key={call.id} call={call} type="scheduled" onStartCall={handleStartCall} onPauseCall={handlePauseCall} onResumeCall={handleResumeCall} onEndCall={handleEndCall} onRetryCall={handleRetryCall} onCancelCall={handleCancelCall} onSendWhatsApp={handleSendWhatsAppSurvey} onViewResults={handleViewSurveyResults} onViewDetails={handleViewCallDetails} />
                  ))
                ) : (
                  <div className="p-8 text-center text-gray-500">
                    No scheduled calls matching your criteria.
                  </div>
                )}
              </div>
              
              {!isCallsLoading && (
                <div className="mt-4 flex justify-end">
                  <Button 
                    onClick={() => showToast("Schedule Batch", "Batch scheduling feature coming soon")}
                  >
                    Schedule Batch
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Completed Calls Tab */}
        <TabsContent value="completed">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Completed Calls</CardTitle>
              <div className="flex items-center space-x-2">
                <Input
                  placeholder="Search..."
                  className="w-64"
                  value={filterValues.search}
                  onChange={(e) => setFilterValues({...filterValues, search: e.target.value})}
                />
                <Select 
                  value={filterValues.surveyType} 
                  onValueChange={(value) => setFilterValues({...filterValues, surveyType: value})}
                >
                  <SelectTrigger className="w-40">
                    <SelectValue placeholder="Survey Type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Surveys</SelectItem>
                    <SelectItem value="Customer Satisfaction">Customer Satisfaction</SelectItem>
                    <SelectItem value="Product Feedback">Product Feedback</SelectItem>
                    <SelectItem value="Technical Support">Technical Support</SelectItem>
                  </SelectContent>
                </Select>
                <Select 
                  value={filterValues.dateRange} 
                  onValueChange={(value) => setFilterValues({...filterValues, dateRange: value})}
                >
                  <SelectTrigger className="w-40">
                    <SelectValue placeholder="Date Range" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Time</SelectItem>
                    <SelectItem value="today">Today</SelectItem>
                    <SelectItem value="week">Last 7 Days</SelectItem>
                    <SelectItem value="month">Last 30 Days</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardHeader>
            
            <CardContent>
              {!isCallsLoading && (
                <div className="flex justify-between items-center mb-4">
                  <p className="text-sm text-gray-500">
                    {getFilteredData(calls.completed).length} completed calls
                  </p>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    className="flex items-center gap-2"
                    onClick={() => showToast("Export CSV", "Export feature coming soon")}
                  >
                    <Download size={16} />
                    Export CSV
                  </Button>
                </div>
              )}
              
              <div className="rounded-md border">
                {isCallsLoading ? (
                  // Show skeleton for completed calls
                  <>
                    {[1, 2, 3, 4, 5, 6].map(i => <CallItemSkeleton key={i} />)}
                  </>
                ) : getFilteredData(calls.completed).length > 0 ? (
                  getFilteredData(calls.completed).map(call => (
                    <CallItem key={call.id} call={call} type="completed" onStartCall={handleStartCall} onPauseCall={handlePauseCall} onResumeCall={handleResumeCall} onEndCall={handleEndCall} onRetryCall={handleRetryCall} onCancelCall={handleCancelCall} onSendWhatsApp={handleSendWhatsAppSurvey} onViewResults={handleViewSurveyResults} onViewDetails={handleViewCallDetails} />
                  ))
                ) : (
                  <div className="p-8 text-center text-gray-500">
                    No completed calls matching your criteria.
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Failed Calls Tab */}
        <TabsContent value="failed">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Failed Calls</CardTitle>
              <Button variant="outline" size="sm" onClick={() => fetchCallData(true)} disabled={isRefreshing}>
                <RefreshCw size={14} className={`mr-2 ${isRefreshing ? "animate-spin" : ""}`} />
                Refresh
              </Button>
            </CardHeader>
            
            <CardContent>
              {!isCallsLoading && (
                <div className="mb-4">
                  <p className="text-sm text-gray-500">
                    {calls.failed.length} failed calls
                  </p>
                </div>
              )}
              
              <div className="rounded-md border">
                {isCallsLoading ? (
                  // Show skeleton for failed calls
                  <>
                    {[1, 2, 3].map(i => <CallItemSkeleton key={i} />)}
                  </>
                ) : calls.failed.length > 0 ? (
                  calls.failed.map(call => (
                    <CallItem key={call.id} call={call} type="failed" onStartCall={handleStartCall} onPauseCall={handlePauseCall} onResumeCall={handleResumeCall} onEndCall={handleEndCall} onRetryCall={handleRetryCall} onCancelCall={handleCancelCall} onSendWhatsApp={handleSendWhatsAppSurvey} onViewResults={handleViewSurveyResults} onViewDetails={handleViewCallDetails} />
                  ))
                ) : (
                  <div className="p-8 text-center text-gray-500">
                    No failed calls.
                  </div>
                )}
              </div>
              
              {!isCallsLoading && (
                <div className="mt-4 flex justify-end">
                  <Button
                    onClick={() => showToast("Retry Failed Calls", "Retry feature coming soon")}
                  >
                    Retry All Failed Calls
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Schedule Call Dialog */}
      <Dialog open={isSchedulingCall} onOpenChange={setIsSchedulingCall}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Schedule New Call</DialogTitle>
            <DialogDescription>
              Schedule a new outbound call with contact information and timing.
            </DialogDescription>
          </DialogHeader>
          
          <div className="grid gap-6 py-4">
            {/* Contact Information - Row 1 */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="phone-number" className="block text-sm font-medium text-gray-700 mb-1">
                  Phone Number *
                </Label>
                <Input
                  id="phone-number"
                  placeholder="+1 (555) 000-0000"
                  className="w-full"
                  value={newCall.phoneNumber}
                  onChange={(e) => setNewCall({...newCall, phoneNumber: e.target.value})}
                />
              </div>
              
              <div>
                <Label htmlFor="contact-name" className="block text-sm font-medium text-gray-700 mb-1">
                  Contact Name *
                </Label>
                <Input
                  id="contact-name"
                  placeholder="John Smith"
                  className="w-full"
                  value={newCall.name}
                  onChange={(e) => setNewCall({...newCall, name: e.target.value})}
                />
              </div>
            </div>

            {/* Call Type Selection */}
            <div className="space-y-3 p-4 bg-gray-50 rounded-lg">
              <Label className="block text-sm font-medium text-gray-700">
                Call Type
              </Label>
              
              <div className="flex space-x-6">
                <div className="flex items-center space-x-2">
                  <input
                    type="radio"
                    id="survey-call"
                    name="callType"
                    checked={!newCall.knowledgeBaseOnly}
                    onChange={() => setNewCall({...newCall, knowledgeBaseOnly: false})}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300"
                  />
                  <Label htmlFor="survey-call" className="text-sm font-medium text-gray-700">
                    Survey-based Call
                  </Label>
                </div>
                
                <div className="flex items-center space-x-2">
                  <input
                    type="radio"
                    id="knowledge-call"
                    name="callType"
                    checked={newCall.knowledgeBaseOnly}
                    onChange={() => setNewCall({...newCall, knowledgeBaseOnly: true})}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300"
                  />
                  <Label htmlFor="knowledge-call" className="text-sm font-medium text-gray-700">
                    Knowledge Base Only
                  </Label>
                </div>
              </div>
              
              <p className="text-xs text-gray-500">
                {newCall.knowledgeBaseOnly 
                  ? "Use knowledge base documents to answer product questions without a survey"
                  : "Use a predefined survey with optional knowledge base enhancement"
                }
              </p>
            </div>

            {/* Survey & Knowledge Base - Row 2 */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="survey-select" className="block text-sm font-medium text-gray-700 mb-1">
                  Survey {!newCall.knowledgeBaseOnly && '*'}
                </Label>
                <Select 
                  value={newCall.surveyId}
                  onValueChange={(value) => setNewCall({...newCall, surveyId: value})}
                  disabled={newCall.knowledgeBaseOnly}
                >
                  <SelectTrigger id="survey-select" className="w-full">
                    <SelectValue placeholder="Select a survey" />
                  </SelectTrigger>
                  <SelectContent>
                    {surveys.map(survey => (
                      <SelectItem key={survey.id} value={survey.id}>
                        {survey.title}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {newCall.knowledgeBaseOnly && (
                  <p className="text-xs text-gray-500 mt-1">
                    Survey not needed for knowledge base inquiries
                  </p>
                )}
              </div>
              
              <div>
                <Label htmlFor="knowledge-base-select" className="block text-sm font-medium text-gray-700 mb-1">
                  Knowledge Base {newCall.knowledgeBaseOnly && '*'}
                </Label>
                <Select 
                  value={newCall.knowledgeBaseId}
                  onValueChange={(value) => setNewCall({...newCall, knowledgeBaseId: value})}
                >
                  <SelectTrigger id="knowledge-base-select" className="w-full">
                    <SelectValue placeholder="Select knowledge base" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">No Knowledge Base</SelectItem>
                    {knowledgeBase.map(kb => (
                      <SelectItem key={kb.id} value={kb.id}>
                        {kb.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {newCall.knowledgeBaseOnly && newCall.knowledgeBaseId === 'none' && (
                  <p className="text-xs text-red-500 mt-1">
                    Knowledge base is required for knowledge base inquiries
                  </p>
                )}
              </div>
            </div>

            {/* Date, Time & Priority - Row 3 */}
            <div className="grid grid-cols-3 gap-4">
              <div>
                <Label htmlFor="scheduled-date" className="block text-sm font-medium text-gray-700 mb-1">
                  Date *
                </Label>
                <Input
                  id="scheduled-date"
                  type="date"
                  className="w-full"
                  value={newCall.scheduledDate}
                  onChange={(e) => setNewCall({...newCall, scheduledDate: e.target.value})}
                />
              </div>
              
              <div>
                <Label htmlFor="scheduled-time" className="block text-sm font-medium text-gray-700 mb-1">
                  Time *
                </Label>
                <Input
                  id="scheduled-time"
                  type="time"
                  className="w-full"
                  value={newCall.scheduledTime}
                  onChange={(e) => setNewCall({...newCall, scheduledTime: e.target.value})}
                />
              </div>
              
              <div>
                <Label htmlFor="priority" className="block text-sm font-medium text-gray-700 mb-1">
                  Priority
                </Label>
                <Select 
                  value={newCall.priority}
                  onValueChange={(value) => setNewCall({...newCall, priority: value})}
                >
                  <SelectTrigger id="priority" className="w-full">
                    <SelectValue placeholder="Select priority" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="high">High</SelectItem>
                    <SelectItem value="normal">Normal</SelectItem>
                    <SelectItem value="low">Low</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            {/* Notes & WhatsApp Toggle - Row 4 */}
            <div className="space-y-4">
              <div>
                <Label htmlFor="notes" className="block text-sm font-medium text-gray-700 mb-1">
                  Notes
                </Label>
                <Input
                  id="notes"
                  placeholder="Optional notes about this call"
                  className="w-full"
                  value={newCall.notes}
                  onChange={(e) => setNewCall({...newCall, notes: e.target.value})}
                />
              </div>
              
              <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg border border-blue-200">
                <div className="flex items-center space-x-3">
                  <Switch 
                    id="send-whatsapp-survey" 
                    checked={newCall.sendWhatsAppSurvey}
                    onCheckedChange={(checked) => setNewCall({...newCall, sendWhatsAppSurvey: checked})}
                  />
                  <div>
                    <Label htmlFor="send-whatsapp-survey" className="text-sm font-medium text-gray-700">
                      Send WhatsApp Message Immediately
                    </Label>
                    <p className="text-xs text-gray-500">
                      {newCall.knowledgeBaseOnly 
                        ? "Send knowledge base inquiry via WhatsApp right after scheduling"
                        : "Send survey link via WhatsApp right after scheduling"
                      }
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <DialogFooter className="flex justify-between items-center">
            <div className="text-xs text-gray-500">
              * Required fields
            </div>
            <div className="flex space-x-2">
              <Button variant="outline" onClick={() => {
                setNewCall({
                  phoneNumber: '',
                  name: '',
                  surveyId: '',
                  knowledgeBaseId: 'none',
                  scheduledDate: '',
                  scheduledTime: '',
                  notes: '',
                  priority: 'normal',
                  sendWhatsAppSurvey: false,
                  knowledgeBaseOnly: false
                });
                setIsSchedulingCall(false);
              }}>
                Cancel
              </Button>
              <Button 
                onClick={handleScheduleCall}
                disabled={
                  !newCall.phoneNumber || 
                  !newCall.name || 
                  (!newCall.knowledgeBaseOnly && !newCall.surveyId) ||
                  (newCall.knowledgeBaseOnly && newCall.knowledgeBaseId === 'none') ||
                  !newCall.scheduledDate || 
                  !newCall.scheduledTime
                }
                className="bg-blue-600 hover:bg-blue-700"
              >
                {newCall.knowledgeBaseOnly 
                  ? (newCall.sendWhatsAppSurvey ? 'Send Knowledge Inquiry' : 'Schedule Knowledge Inquiry')
                  : (newCall.sendWhatsAppSurvey ? 'Schedule & Send Survey' : 'Schedule Call')
                }
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default CallManagement;