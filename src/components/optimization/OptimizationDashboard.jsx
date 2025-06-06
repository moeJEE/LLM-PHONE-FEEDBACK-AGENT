import React, { useState, useEffect } from 'react';
import { useAuth } from '@clerk/clerk-react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar
} from 'recharts';
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Zap,
  Activity,
  Target,
  Clock,
  CheckCircle,
  AlertTriangle,
  Settings
} from 'lucide-react';
import { optimizationAPI } from '../../services/api';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

const OptimizationDashboard = () => {
  const { getToken } = useAuth();
  const [analytics, setAnalytics] = useState(null);
  const [insights, setInsights] = useState(null);
  const [costBreakdown, setCostBreakdown] = useState(null);
  const [ragPerformance, setRagPerformance] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [timeRange, setTimeRange] = useState(7);

  useEffect(() => {
    fetchOptimizationData();
  }, [timeRange]);

  const fetchOptimizationData = async () => {
    try {
      setLoading(true);
      const authToken = await getToken();
      const response = await fetch(`${API_BASE_URL}/api/optimization/recommendations`, {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch optimization data');
      }
      
      const data = await response.json();
      setAnalytics(data.analytics);
      setInsights(data.insights);
      setCostBreakdown(data.costBreakdown);
      setRagPerformance(data.ragPerformance);
    } catch (error) {
      // Handle error silently or show user-friendly message
    } finally {
      setLoading(false);
    }
  };

  const applyRecommendation = async (recommendationId) => {
    try {
      const authToken = await getToken();
      const response = await fetch(`${API_BASE_URL}/api/optimization/apply/${recommendationId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to apply recommendation');
      }
      
      // Refresh data after applying recommendation
      await fetchOptimizationData();
    } catch (error) {
      // Handle error silently or show user-friendly message
    }
  };

  const runOptimizationTest = async () => {
    try {
      setLoading(true);
      const authToken = await getToken();
      const response = await fetch(`${API_BASE_URL}/api/optimization/test`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to run optimization test');
      }
      
      await fetchOptimizationData();
    } catch (error) {
      // Handle error silently or show user-friendly message
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 4
    }).format(amount);
  };

  const formatNumber = (num) => {
    return new Intl.NumberFormat('en-US').format(num);
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'high':
      case 'critical':
        return 'destructive';
      case 'medium':
        return 'default';
      case 'low':
        return 'secondary';
      default:
        return 'outline';
    }
  };

  if (loading) {
    return (
      <div className="p-6 space-y-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-32 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Optimization Dashboard</h1>
          <p className="text-muted-foreground">
            Monitor and optimize your AI token usage and costs
          </p>
        </div>
        <div className="flex gap-2">
          {[7, 14, 30].map((days) => (
            <Button
              key={days}
              variant={timeRange === days ? "default" : "outline"}
              size="sm"
              onClick={() => setTimeRange(days)}
            >
              {days}d
            </Button>
          ))}
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Tokens</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatNumber(analytics?.total_tokens || 0)}
            </div>
            <p className="text-xs text-muted-foreground">
              {analytics?.total_requests || 0} requests
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Cost</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatCurrency(costBreakdown?.total_cost_usd || 0)}
            </div>
            <p className="text-xs text-muted-foreground">
              {formatCurrency(costBreakdown?.projected_monthly_cost || 0)} projected monthly
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Cache Hit Rate</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {((analytics?.cache_hit_rate || 0) * 100).toFixed(1)}%
            </div>
            <p className="text-xs text-muted-foreground">
              {analytics?.cached_requests || 0} cached requests
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Optimization Score</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {insights?.optimization_score || 0}/100
            </div>
            <p className="text-xs text-muted-foreground">
              {insights?.potential_savings?.percentage || 0}% potential savings
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="costs">Costs</TabsTrigger>
          <TabsTrigger value="rag">RAG Performance</TabsTrigger>
          <TabsTrigger value="recommendations">Recommendations</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          {/* Usage Trends */}
          <Card>
            <CardHeader>
              <CardTitle>Token Usage Trends</CardTitle>
              <CardDescription>
                Daily token consumption over the selected period
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart
                  data={Object.entries(analytics?.daily_breakdown || {}).map(([date, usage]) => ({
                    date: new Date(date).toLocaleDateString(),
                    tokens: usage.tokens,
                    requests: usage.requests
                  }))}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="tokens" stroke="#8884d8" />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Service Breakdown */}
          <Card>
            <CardHeader>
              <CardTitle>Usage by Service Type</CardTitle>
              <CardDescription>
                Token distribution across different AI services
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={Object.entries(analytics?.type_breakdown || {}).map(([type, usage], index) => ({
                      name: type.replace('_', ' ').toUpperCase(),
                      value: usage.tokens,
                      fill: COLORS[index % COLORS.length]
                    }))}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    dataKey="value"
                  >
                    {Object.entries(analytics?.type_breakdown || {}).map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="costs" className="space-y-6">
          {/* Cost Breakdown */}
          <Card>
            <CardHeader>
              <CardTitle>Cost Analysis</CardTitle>
              <CardDescription>
                Detailed breakdown of costs by service and time
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="text-center p-4 border rounded">
                    <div className="text-2xl font-bold text-green-600">
                      {formatCurrency(costBreakdown?.average_cost_per_request || 0)}
                    </div>
                    <div className="text-sm text-muted-foreground">Avg Cost per Request</div>
                  </div>
                  <div className="text-center p-4 border rounded">
                    <div className="text-2xl font-bold text-blue-600">
                      {formatCurrency(costBreakdown?.projected_monthly_cost || 0)}
                    </div>
                    <div className="text-sm text-muted-foreground">Projected Monthly</div>
                  </div>
                  <div className="text-center p-4 border rounded">
                    <div className="text-2xl font-bold text-orange-600">
                      {formatCurrency(costBreakdown?.optimization_potential?.potential_monthly_savings || 0)}
                    </div>
                    <div className="text-sm text-muted-foreground">Potential Savings</div>
                  </div>
                </div>

                <ResponsiveContainer width="100%" height={300}>
                  <BarChart
                    data={Object.entries(costBreakdown?.cost_by_service || {}).map(([service, data]) => ({
                      service: service.replace('_', ' ').toUpperCase(),
                      cost: data.cost_usd,
                      tokens: data.tokens
                    }))}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="service" />
                    <YAxis />
                    <Tooltip formatter={(value, name) => [
                      name === 'cost' ? formatCurrency(value) : formatNumber(value),
                      name === 'cost' ? 'Cost' : 'Tokens'
                    ]} />
                    <Bar dataKey="cost" fill="#8884d8" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="rag" className="space-y-6">
          {/* RAG Performance Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">RAG Queries</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {formatNumber(ragPerformance?.total_rag_queries || 0)}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Avg Tokens/Query</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {ragPerformance?.average_tokens_per_query || 0}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Compression Ratio</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {((ragPerformance?.compression_ratio || 0) * 100).toFixed(0)}%
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Token Savings</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {formatNumber(ragPerformance?.estimated_token_savings || 0)}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* RAG Strategies */}
          <Card>
            <CardHeader>
              <CardTitle>Retrieval Strategy Performance</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart
                  data={Object.entries(ragPerformance?.retrieval_strategies_used || {}).map(([strategy, usage]) => ({
                    strategy: strategy.charAt(0).toUpperCase() + strategy.slice(1),
                    usage
                  }))}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="strategy" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="usage" fill="#82ca9d" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="recommendations" className="space-y-6">
          <div className="grid gap-4">
            {insights?.recommendations?.map((rec, index) => (
              <Card key={index}>
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div>
                      <CardTitle className="flex items-center gap-2">
                        {rec.priority === 'high' || rec.priority === 'critical' ? (
                          <AlertTriangle className="h-4 w-4 text-red-500" />
                        ) : (
                          <CheckCircle className="h-4 w-4 text-green-500" />
                        )}
                        {rec.type.replace('_', ' ').toUpperCase()}
                      </CardTitle>
                      <CardDescription className="mt-1">
                        {rec.description}
                      </CardDescription>
                    </div>
                    <div className="flex gap-2">
                      <Badge variant={getPriorityColor(rec.priority)}>
                        {rec.priority}
                      </Badge>
                      <Badge variant="outline">
                        {rec.implementation_effort} effort
                      </Badge>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex justify-between items-center">
                    <div>
                      <p className="text-sm text-muted-foreground">
                        Potential savings: {rec.potential_savings}
                      </p>
                    </div>
                    <Button
                      size="sm"
                      onClick={() => handleApplyRecommendation(rec.type)}
                      className="flex items-center gap-2"
                    >
                      <Settings className="h-4 w-4" />
                      Apply
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {(!insights?.recommendations || insights.recommendations.length === 0) && (
            <Alert>
              <CheckCircle className="h-4 w-4" />
              <AlertDescription>
                Great! Your system is well optimized. No immediate recommendations available.
              </AlertDescription>
            </Alert>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default OptimizationDashboard; 