import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { useAuth, useUser } from '@clerk/clerk-react';
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardHeader, 
  CardTitle 
} from '@/components/ui/card';
import { 
  Tabs, 
  TabsContent, 
  TabsList, 
  TabsTrigger 
} from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { 
  LineChart, 
  Line, 
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area,
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer 
} from 'recharts';
import { 
  PhoneCall, 
  PhoneIncoming,
  PhoneOutgoing,
  PhoneMissed,
  BarChart2,
  TrendingUp,
  Users,
  Clock,
  Calendar,
  ArrowUpRight,
  ArrowDownRight,
  Plus,
  Loader2,
  RefreshCw
} from 'lucide-react';
import { 
  testBackendConnection,
  getDashboardAnalytics,
  getSentimentAnalytics,
  getCallVolumeAnalytics,
  getCalls,
  getCallStats
} from '@/services/api';

// Skeleton Components
const StatCardSkeleton = () => (
  <Card>
    <CardHeader className="pb-2">
      <Skeleton className="h-4 w-24" />
    </CardHeader>
    <CardContent>
      <Skeleton className="h-8 w-16 mb-2" />
      <Skeleton className="h-3 w-20" />
    </CardContent>
  </Card>
);

const ChartSkeleton = ({ height = 300 }) => (
  <div className={`w-full h-[${height}px] flex items-center justify-center`}>
    <div className="animate-pulse flex space-x-4 w-full h-full">
      <div className="rounded bg-gray-200 w-full h-full flex items-center justify-center">
        <BarChart2 className="h-12 w-12 text-gray-400" />
      </div>
    </div>
  </div>
);

const CallItemSkeleton = () => (
  <div className="flex items-center justify-between p-3 border-b last:border-b-0">
    <div className="flex items-center space-x-3">
      <Skeleton className="h-8 w-8 rounded-full" />
      <div>
        <Skeleton className="h-4 w-32 mb-1" />
        <Skeleton className="h-3 w-24" />
      </div>
    </div>
    <div className="text-right">
      <Skeleton className="h-3 w-16 mb-1" />
      <Skeleton className="h-3 w-12" />
    </div>
  </div>
);

const UpcomingCallSkeleton = () => (
  <div className="flex items-center justify-between p-3 border rounded-lg">
    <div className="flex items-center space-x-3">
      <Skeleton className="h-8 w-8 rounded-full" />
      <div>
        <Skeleton className="h-4 w-32 mb-1" />
        <Skeleton className="h-3 w-24" />
      </div>
    </div>
    <Skeleton className="h-3 w-16" />
  </div>
);

const Dashboard = () => {
  const [apiStatus, setApiStatus] = useState('unknown');
  const [isLoading, setIsLoading] = useState(true);
  const [isStatsLoading, setIsStatsLoading] = useState(true);
  const [isChartsLoading, setIsChartsLoading] = useState(true);
  const [isCallsLoading, setIsCallsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState(null);
  
  // Real data states
  const [callStats, setCallStats] = useState(null);
  const [callVolumeData, setCallVolumeData] = useState([]);
  const [sentimentData, setSentimentData] = useState([]);
  const [recentCalls, setRecentCalls] = useState([]);
  const [feedbackTopicsData, setFeedbackTopicsData] = useState([]);
  const [completionRateData, setCompletionRateData] = useState([]);
  const [upcomingCalls, setUpcomingCalls] = useState([]);

  // Memoized helper functions
  const formatDuration = useCallback((seconds) => {
    if (!seconds || seconds === 0) return '0:00';
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  }, []);

  const formatTimeAgo = useCallback((timestamp) => {
    const now = new Date();
    const callTime = new Date(timestamp);
    const diffMs = now - callTime;
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffMins = Math.floor(diffMs / (1000 * 60));
    
    if (diffHours > 24) {
      return `${Math.floor(diffHours / 24)}d ago`;
    } else if (diffHours > 0) {
      return `${diffHours}h ago`;
    } else if (diffMins > 0) {
      return `${diffMins}m ago`;
    } else {
      return 'Just now';
    }
  }, []);

  const formatScheduledTime = useCallback((timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const isToday = date.toDateString() === now.toDateString();
    
    if (isToday) {
      return `Today at ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    } else {
      return date.toLocaleDateString([], { 
        month: 'short', 
        day: 'numeric',
        hour: '2-digit', 
        minute: '2-digit' 
      });
    }
  }, []);

  const generateCompletionRateData = useCallback(() => {
    return [
      { name: 'Mon', completion: 85, target: 90 },
      { name: 'Tue', completion: 92, target: 90 },
      { name: 'Wed', completion: 78, target: 90 },
      { name: 'Thu', completion: 88, target: 90 },
      { name: 'Fri', completion: 95, target: 90 },
      { name: 'Sat', completion: 82, target: 90 },
      { name: 'Sun', completion: 76, target: 90 }
    ];
  }, []);

  // Optimized data loading functions
  const loadStatsData = useCallback(async (token, isRefresh = false) => {
    try {
      if (!isRefresh) {
        setIsStatsLoading(true);
      }
      const dashboardData = await getDashboardAnalytics('month', token);
      setCallStats(dashboardData.callStats);
      
      // Generate feedback topics from survey stats
      if (dashboardData.surveyStats?.survey_type_distribution) {
        const topics = Object.entries(dashboardData.surveyStats.survey_type_distribution)
          .map(([name, value]) => ({ name, value }))
          .filter(topic => topic.value > 0);
        setFeedbackTopicsData(topics);
      } else {
        setFeedbackTopicsData([
          { name: 'Customer Satisfaction', value: 50 },
          { name: 'Product Feedback', value: 30 },
          { name: 'Technical Support', value: 20 }
        ]);
      }
      
      return dashboardData;
    } finally {
      if (!isRefresh) {
        setIsStatsLoading(false);
      }
    }
  }, []);

  const loadChartsData = useCallback(async (token, isRefresh = false) => {
    try {
      if (!isRefresh) {
        setIsChartsLoading(true);
      }
      const [volumeData, sentimentAnalytics] = await Promise.all([
        getCallVolumeAnalytics('week', token),
        getSentimentAnalytics('month', token)
      ]);
      
      setCallVolumeData(volumeData);
      setSentimentData(sentimentAnalytics);
      setCompletionRateData(generateCompletionRateData());
    } finally {
      if (!isRefresh) {
        setIsChartsLoading(false);
      }
    }
  }, [generateCompletionRateData]);

  const loadCallsData = useCallback(async (token, dashboardData, isRefresh = false) => {
    try {
      if (!isRefresh) {
        setIsCallsLoading(true);
      }
      const callsData = await getCalls({ limit: 10, status: 'all' }, token);
      
      // Process recent calls
      if (callsData && Array.isArray(callsData)) {
        const formattedCalls = callsData.slice(0, 4).map(call => ({
          id: call.id,
          type: call.call_type || 'outbound',
          name: call.contact_name || 'Unknown Contact',
          number: call.phone_number,
          duration: formatDuration(call.metadata?.duration_seconds),
          status: call.status,
          time: formatTimeAgo(call.created_at),
          sentiment: call.metadata?.overall_sentiment ? 
            (call.metadata.overall_sentiment > 0.1 ? 'positive' : 
             call.metadata.overall_sentiment < -0.1 ? 'negative' : 'neutral') : 'n/a'
        }));
        setRecentCalls(formattedCalls);
        
        // Get upcoming scheduled calls
        const scheduledCalls = callsData.filter(call => 
          call.status === 'scheduled' && call.scheduled_time && new Date(call.scheduled_time) > new Date()
        ).slice(0, 3).map(call => ({
          id: call.id,
          name: call.contact_name || 'Unknown Contact',
          number: call.phone_number,
          time: formatScheduledTime(call.scheduled_time),
          type: dashboardData?.surveyStats?.survey_type_distribution ? 
            Object.keys(dashboardData.surveyStats.survey_type_distribution)[0] : 'Customer Satisfaction'
        }));
        setUpcomingCalls(scheduledCalls);
      } else {
        setRecentCalls([]);
        setUpcomingCalls([]);
      }
    } finally {
      if (!isRefresh) {
        setIsCallsLoading(false);
      }
    }
  }, [formatDuration, formatTimeAgo, formatScheduledTime]);

  const loadDashboardData = useCallback(async (refresh = false) => {
    try {
      if (refresh) {
        setIsRefreshing(true);
        // When refreshing, also set individual loading states to show proper loading indicators
        setIsStatsLoading(true);
        setIsChartsLoading(true);
        setIsCallsLoading(true);
      } else {
        setIsLoading(true);
      }
      setError(null);
      
      // Test API connection first
      try {
        const result = await testBackendConnection();
        setApiStatus(result.status || 'connected');
      } catch (error) {
        setApiStatus('error');
      }
      
      // Get auth token
      let token = null;
      try {
        const { getToken } = useAuth();
        token = await getToken();
      } catch (error) {
        // Continue without auth for demo purposes
      }

      // Load data in parallel for better performance
      const dashboardData = await loadStatsData(token, refresh);
      await Promise.all([
        loadChartsData(token, refresh),
        loadCallsData(token, dashboardData, refresh)
      ]);

    } catch (error) {
      setError(error.message);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
      // When refreshing, also reset individual loading states
      if (refresh) {
        setIsStatsLoading(false);
        setIsChartsLoading(false);
        setIsCallsLoading(false);
      }
    }
  }, [getToken, loadStatsData, loadChartsData, loadCallsData]);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  // Generate stats from real data
  const stats = callStats ? [
    { 
      title: 'Total Calls', 
      value: callStats.total_calls?.toString() || '0', 
      change: '+12.5%', // This could be calculated from historical data
      trend: 'up',
      icon: <PhoneCall className="h-4 w-4 text-blue-500" />,
      description: 'This month'
    },
    { 
      title: 'Avg. Duration', 
      value: formatDuration(callStats.average_duration_seconds) || '0:00', 
      change: '-1:15', // This could be calculated from historical data
      trend: 'down',
      icon: <Clock className="h-4 w-4 text-green-500" />,
      description: 'Per call'
    },
    { 
      title: 'Completed Calls', 
      value: callStats.completed_calls?.toString() || '0', 
      change: '+3.2%',
      trend: 'up',
      icon: <TrendingUp className="h-4 w-4 text-purple-500" />,
      description: 'Successfully completed'
    },
    { 
      title: 'Scheduled Calls', 
      value: callStats.scheduled_calls?.toString() || '0', 
      change: '+4.1%',
      trend: 'up',
      icon: <Users className="h-4 w-4 text-yellow-500" />,
      description: 'Upcoming calls'
    }
  ] : [];
  
  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#A569BD'];
  
  const StatCard = ({ stat }) => (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500">{stat.title}</p>
            <div className="flex items-baseline mt-1">
              <h3 className="text-2xl font-bold">{stat.value}</h3>
              <div className={`ml-2 flex items-center text-xs font-medium ${
                stat.trend === 'up' ? 'text-green-600' : 'text-red-600'
              }`}>
                {stat.trend === 'up' ? (
                  <ArrowUpRight className="h-3 w-3 mr-1" />
                ) : (
                  <ArrowDownRight className="h-3 w-3 mr-1" />
                )}
                {stat.change}
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-1">{stat.description}</p>
          </div>
          <div className="p-2 rounded-full bg-gray-100">
            {stat.icon}
          </div>
        </div>
      </CardContent>
    </Card>
  );

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <p className="text-red-600 mb-2">Error loading dashboard: {error}</p>
          <Button onClick={() => window.location.reload()}>
            Retry
          </Button>
        </div>
      </div>
    );
  }
  
  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-gray-500">Welcome back! Here's an overview of your call system.</p>
        </div>
        <div className="flex items-center space-x-2">
          <div className={`px-3 py-1 rounded-full text-xs font-medium ${
            apiStatus === 'connected' ? 'bg-green-100 text-green-800' : 
            apiStatus === 'error' ? 'bg-red-100 text-red-800' : 
            'bg-yellow-100 text-yellow-800'
          }`}>
            API: {apiStatus}
          </div>
          <Button onClick={() => loadDashboardData(true)} disabled={isRefreshing}>
            <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button>
            <Calendar className="h-4 w-4 mr-2" />
            This Month
          </Button>
          <Button variant="outline">
            <Calendar className="h-4 w-4 mr-2" />
            Compare
          </Button>
        </div>
      </div>
      
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-6">
        {isStatsLoading ? (
          <>
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
          </>
        ) : (
          stats.map((stat, index) => (
            <StatCard key={index} stat={stat} />
          ))
        )}
      </div>
      
      <div className="grid gap-6 md:grid-cols-2 mb-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div>
              <CardTitle>Call Volume</CardTitle>
              <CardDescription>Inbound vs outbound calls</CardDescription>
            </div>
            <Tabs defaultValue="week">
              <TabsList className="grid grid-cols-3 h-8 w-40">
                <TabsTrigger value="day" className="text-xs">Day</TabsTrigger>
                <TabsTrigger value="week" className="text-xs">Week</TabsTrigger>
                <TabsTrigger value="month" className="text-xs">Month</TabsTrigger>
              </TabsList>
            </Tabs>
          </CardHeader>
          <CardContent className="pt-2">
            {isChartsLoading ? (
              <ChartSkeleton height={320} />
            ) : (
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={callVolumeData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="inbound" fill="#8884d8" name="Inbound" />
                    <Bar dataKey="outbound" fill="#82ca9d" name="Outbound" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div>
              <CardTitle>Sentiment Analysis</CardTitle>
              <CardDescription>Customer feedback sentiment</CardDescription>
            </div>
            <Tabs defaultValue="month">
              <TabsList className="grid grid-cols-3 h-8 w-40">
                <TabsTrigger value="week" className="text-xs">Week</TabsTrigger>
                <TabsTrigger value="month" className="text-xs">Month</TabsTrigger>
                <TabsTrigger value="year" className="text-xs">Year</TabsTrigger>
              </TabsList>
            </Tabs>
          </CardHeader>
          <CardContent className="pt-2">
            {isChartsLoading ? (
              <ChartSkeleton height={320} />
            ) : (
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={sentimentData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Area type="monotone" dataKey="positive" stackId="1" stroke="#82ca9d" fill="#82ca9d" name="Positive" />
                    <Area type="monotone" dataKey="neutral" stackId="1" stroke="#8884d8" fill="#8884d8" name="Neutral" />
                    <Area type="monotone" dataKey="negative" stackId="1" stroke="#ff7c7c" fill="#ff7c7c" name="Negative" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
      
      <div className="grid gap-6 md:grid-cols-3">
        <Card className="md:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Recent Calls</CardTitle>
              <CardDescription>Latest call activity</CardDescription>
            </div>
            <Button variant="outline" size="sm">
              View All
            </Button>
          </CardHeader>
          <CardContent>
            {isCallsLoading ? (
              <div className="space-y-0 divide-y">
                <CallItemSkeleton />
                <CallItemSkeleton />
                <CallItemSkeleton />
                <CallItemSkeleton />
              </div>
            ) : recentCalls.length > 0 ? (
              <div className="space-y-0 divide-y">
                {recentCalls.map(call => (
                  <div key={call.id} className="flex items-center justify-between p-3 hover:bg-gray-50 transition-colors">
                    <div className="flex items-center space-x-3">
                      <div className={`p-2 rounded-full ${
                        call.type === 'inbound' ? 'bg-green-100' : 'bg-blue-100'
                      }`}>
                        {call.type === 'inbound' ? (
                          <PhoneIncoming className="h-4 w-4 text-green-600" />
                        ) : (
                          <PhoneOutgoing className="h-4 w-4 text-blue-600" />
                        )}
                      </div>
                      <div>
                        <p className="font-medium">{call.name}</p>
                        <p className="text-sm text-gray-500">{call.number}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-medium">{call.duration}</p>
                      <p className="text-xs text-gray-500">{call.time}</p>
                      <div className={`inline-block px-2 py-1 text-xs rounded-full mt-1 ${
                        call.sentiment === 'positive' ? 'bg-green-100 text-green-800' :
                        call.sentiment === 'negative' ? 'bg-red-100 text-red-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {call.sentiment}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                No recent calls available
              </div>
            )}
          </CardContent>
        </Card>
        
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Upcoming Calls</CardTitle>
              <CardDescription>Scheduled for today</CardDescription>
            </CardHeader>
            <CardContent>
              {isCallsLoading ? (
                <div className="space-y-3">
                  <UpcomingCallSkeleton />
                  <UpcomingCallSkeleton />
                  <UpcomingCallSkeleton />
                </div>
              ) : upcomingCalls.length > 0 ? (
                <div className="space-y-3">
                  {upcomingCalls.map(call => (
                    <div key={call.id} className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex items-center space-x-3">
                        <div className="p-2 rounded-full bg-blue-100">
                          <Calendar className="h-4 w-4 text-blue-600" />
                        </div>
                        <div>
                          <p className="font-medium text-sm">{call.name}</p>
                          <p className="text-xs text-gray-500">{call.type}</p>
                        </div>
                      </div>
                      <p className="text-xs text-gray-500">{call.time}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-4 text-gray-500 text-sm">
                  No upcoming calls
                </div>
              )}
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader>
              <CardTitle>Feedback Topics</CardTitle>
              <CardDescription>Survey distribution</CardDescription>
            </CardHeader>
            <CardContent>
              {isStatsLoading ? (
                <ChartSkeleton height={200} />
              ) : (
                <div className="h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={feedbackTopicsData}
                        cx="50%"
                        cy="50%"
                        innerRadius={40}
                        outerRadius={80}
                        paddingAngle={5}
                        dataKey="value"
                      >
                        {feedbackTopicsData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;