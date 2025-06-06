import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  PhoneCall, 
  Shield, 
  Settings, 
  AlertTriangle, 
  CheckCircle, 
  Copy, 
  Eye, 
  EyeOff, 
  RefreshCw,
  ArrowLeft,
  Plus,
  Save,
  Trash2
} from 'lucide-react';

import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { 
  Table, 
  TableBody, 
  TableCaption, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

const TwilioIntegration = () => {
  const navigate = useNavigate();
  const [connectionStatus, setConnectionStatus] = useState('connected'); // connected, disconnected, connecting
  const [showCredentials, setShowCredentials] = useState(false);
  const [phoneNumbers, setPhoneNumbers] = useState([]);
  const [callLogs, setCallLogs] = useState([]);
  const [formChanged, setFormChanged] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [error, setError] = useState('');
  
  const [twilioSettings, setTwilioSettings] = useState({
    accountSid: 'AC1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p',
    authToken: '1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p',
    defaultRegion: 'US',
    webhookUrl: 'https://your-app.com/api/twilio/webhook',
    callRecording: true,
    recordingConsent: true,
    maxConcurrentCalls: 5,
    retryAttempts: 3,
    callTimeout: 30,
    callbackUrl: 'https://your-app.com/api/twilio/callback',
    fallbackUrl: 'https://your-app.com/api/twilio/fallback'
  });

  // Simulated data fetch
  useEffect(() => {
    setPhoneNumbers([
      { id: 1, number: '+1 (555) 123-4567', region: 'US', active: true, assignedTo: 'Main Customer Support', monthlyUsage: 243 },
      { id: 2, number: '+1 (555) 987-6543', region: 'US', active: true, assignedTo: 'Feedback Collection', monthlyUsage: 156 },
      { id: 3, number: '+1 (555) 234-5678', region: 'US', active: false, assignedTo: 'Unassigned', monthlyUsage: 0 }
    ]);

    setCallLogs([
      { id: 'log1', timestamp: '2025-04-05 09:23:45', direction: 'outbound', from: '+1 (555) 123-4567', to: '+1 (555) 111-2222', duration: 183, status: 'completed', cost: 0.0075 },
      { id: 'log2', timestamp: '2025-04-05 10:12:33', direction: 'inbound', from: '+1 (555) 333-4444', to: '+1 (555) 123-4567', duration: 247, status: 'completed', cost: 0.0085 },
      { id: 'log3', timestamp: '2025-04-05 11:05:12', direction: 'outbound', from: '+1 (555) 987-6543', to: '+1 (555) 555-6666', duration: 0, status: 'failed', cost: 0.0020 }
    ]);
  }, []);

  const handleTestConnection = () => {
    setConnectionStatus('connecting');
    setTimeout(() => {
      setConnectionStatus('connected');
    }, 1500);
  };

  const handleSettingsChange = (field, value) => {
    setTwilioSettings(prev => ({ ...prev, [field]: value }));
    setFormChanged(true);
  };

  const maskCredential = (credential) => {
    if (!credential) return '';
    return showCredentials ? credential : credential.substring(0, 4) + '••••••••••••••••' + credential.substring(credential.length - 4);
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    // In a real app, you would show a toast notification here
  };

  const handleSaveSettings = async () => {
    try {
      setIsSaving(true);
      
      // Validate required fields
      if (!twilioSettings.accountSid || !twilioSettings.authToken || !twilioSettings.phoneNumber) {
        setError('Please fill in all required fields');
        return;
      }

      // Save settings to the API
      const authToken = await getToken();
      const response = await fetch(`${API_BASE_URL}/api/twilio/settings`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify(twilioSettings)
      });

      if (!response.ok) {
        throw new Error('Failed to save Twilio settings');
      }

      setSuccessMessage('Twilio settings saved successfully!');
      setError('');
      
      // Clear success message after 3 seconds
      setTimeout(() => setSuccessMessage(''), 3000);
      
    } catch (error) {
      setError(error.message || 'Failed to save Twilio settings');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="p-6">
      <Button 
        variant="ghost" 
        className="mb-6 pl-0 flex items-center text-gray-500 hover:text-gray-900"
        onClick={() => navigate('/settings')}
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to Settings
      </Button>

      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold">Twilio Integration</h1>
          <p className="text-gray-500">Configure your Twilio settings for phone call functionality</p>
        </div>
        <div className="flex items-center space-x-2">
          <Button 
            variant="outline" 
            onClick={() => setTwilioSettings({
              accountSid: '',
              authToken: '',
              defaultRegion: 'US',
              webhookUrl: '',
              callRecording: false,
              recordingConsent: true,
              maxConcurrentCalls: 5,
              retryAttempts: 3,
              callTimeout: 30,
              callbackUrl: '',
              fallbackUrl: ''
            })}
          >
            <Trash2 className="mr-2 h-4 w-4" />
            Reset
          </Button>
          <Button 
            onClick={handleSaveSettings}
            disabled={!formChanged}
          >
            <Save className="mr-2 h-4 w-4" />
            Save Changes
          </Button>
        </div>
      </div>

      <Tabs defaultValue="credentials">
        <TabsList className="mb-6">
          <TabsTrigger value="credentials">Credentials</TabsTrigger>
          <TabsTrigger value="phone-numbers">Phone Numbers</TabsTrigger>
          <TabsTrigger value="call-settings">Call Settings</TabsTrigger>
          <TabsTrigger value="webhooks">Webhooks</TabsTrigger>
          <TabsTrigger value="logging">Logging</TabsTrigger>
        </TabsList>
        
        <TabsContent value="credentials">
          <Card>
            <CardHeader>
              <div className="flex justify-between items-center">
                <div>
                  <CardTitle>Twilio Credentials</CardTitle>
                  <CardDescription>Connect your Twilio account to enable phone calling</CardDescription>
                </div>
                <Badge className={connectionStatus === 'connected' ? 'bg-green-500' : connectionStatus === 'connecting' ? 'bg-yellow-500' : 'bg-red-500'}>
                  {connectionStatus === 'connected' ? 'Connected' : connectionStatus === 'connecting' ? 'Connecting...' : 'Disconnected'}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="account-sid">Account SID</Label>
                <div className="flex">
                  <Input 
                    id="account-sid"
                    className="rounded-r-none"
                    value={maskCredential(twilioSettings.accountSid)} 
                    onChange={(e) => handleSettingsChange('accountSid', e.target.value)}
                    readOnly={!showCredentials}
                  />
                  <Button 
                    variant="outline" 
                    className="rounded-l-none border-l-0"
                    onClick={() => copyToClipboard(twilioSettings.accountSid)}
                  >
                    <Copy size={16} />
                  </Button>
                </div>
                <p className="text-xs text-gray-500">Your Twilio Account SID from your Twilio dashboard</p>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="auth-token">Auth Token</Label>
                <div className="flex">
                  <Input 
                    id="auth-token"
                    className="rounded-r-none"
                    type={showCredentials ? "text" : "password"}
                    value={maskCredential(twilioSettings.authToken)} 
                    onChange={(e) => handleSettingsChange('authToken', e.target.value)}
                    readOnly={!showCredentials}
                  />
                  <Button 
                    variant="outline" 
                    className="rounded-l-none border-l-0"
                    onClick={() => copyToClipboard(twilioSettings.authToken)}
                  >
                    <Copy size={16} />
                  </Button>
                </div>
                <p className="text-xs text-gray-500">Your Twilio Auth Token from your Twilio dashboard</p>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="default-region">Default Region</Label>
                <Select
                  value={twilioSettings.defaultRegion}
                  onValueChange={(value) => handleSettingsChange('defaultRegion', value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select a region" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="US">United States</SelectItem>
                    <SelectItem value="CA">Canada</SelectItem>
                    <SelectItem value="GB">United Kingdom</SelectItem>
                    <SelectItem value="AU">Australia</SelectItem>
                    <SelectItem value="DE">Germany</SelectItem>
                    <SelectItem value="FR">France</SelectItem>
                    <SelectItem value="JP">Japan</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-gray-500">The default region for phone numbers</p>
              </div>
              
              <div className="flex items-center space-x-4 pt-4">
                <Button variant="outline" onClick={() => setShowCredentials(!showCredentials)}>
                  {showCredentials ? <EyeOff size={16} className="mr-2" /> : <Eye size={16} className="mr-2" />}
                  {showCredentials ? 'Hide Credentials' : 'Show Credentials'}
                </Button>
                
                <Button 
                  variant={connectionStatus === 'connecting' ? 'outline' : 'default'}
                  onClick={handleTestConnection}
                  disabled={connectionStatus === 'connecting'}
                >
                  <RefreshCw size={16} className={`mr-2 ${connectionStatus === 'connecting' ? 'animate-spin' : ''}`} />
                  Test Connection
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="phone-numbers">
          <Card>
            <CardHeader>
              <div className="flex justify-between items-center">
                <div>
                  <CardTitle>Phone Numbers</CardTitle>
                  <CardDescription>Manage your Twilio phone numbers</CardDescription>
                </div>
                <Button>
                  <Plus className="mr-2 h-4 w-4" />
                  Add Phone Number
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Phone Number</TableHead>
                    <TableHead>Region</TableHead>
                    <TableHead>Assigned To</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Monthly Usage</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {phoneNumbers.map(number => (
                    <TableRow key={number.id}>
                      <TableCell className="font-medium">{number.number}</TableCell>
                      <TableCell>{number.region}</TableCell>
                      <TableCell>{number.assignedTo}</TableCell>
                      <TableCell>
                        <Badge
                          className={number.active ? 'bg-green-500' : 'bg-gray-500'}
                        >
                          {number.active ? 'Active' : 'Inactive'}
                        </Badge>
                      </TableCell>
                      <TableCell>{number.monthlyUsage} calls</TableCell>
                      <TableCell className="text-right">
                        <Button variant="ghost" size="sm">Configure</Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="call-settings">
          <Card>
            <CardHeader>
              <CardTitle>Call Settings</CardTitle>
              <CardDescription>Configure how calls are made and handled</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label htmlFor="max-concurrent-calls">Maximum Concurrent Calls</Label>
                  <Input 
                    id="max-concurrent-calls" 
                    type="number" 
                    min="1"
                    max="100"
                    value={twilioSettings.maxConcurrentCalls}
                    onChange={(e) => handleSettingsChange('maxConcurrentCalls', parseInt(e.target.value))}
                  />
                  <p className="text-xs text-gray-500">Maximum number of calls to make simultaneously</p>
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="retry-attempts">Retry Attempts</Label>
                  <Input 
                    id="retry-attempts" 
                    type="number"
                    min="0"
                    max="10" 
                    value={twilioSettings.retryAttempts}
                    onChange={(e) => handleSettingsChange('retryAttempts', parseInt(e.target.value))}
                  />
                  <p className="text-xs text-gray-500">Number of times to retry failed calls</p>
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="call-timeout">Call Timeout (seconds)</Label>
                  <Input 
                    id="call-timeout" 
                    type="number" 
                    min="10"
                    max="120"
                    value={twilioSettings.callTimeout}
                    onChange={(e) => handleSettingsChange('callTimeout', parseInt(e.target.value))}
                  />
                  <p className="text-xs text-gray-500">How long to wait for an answer before timing out</p>
                </div>
              </div>
              
              <Separator />
              
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="call-recording">Call Recording</Label>
                    <p className="text-xs text-gray-500">Enable recording of all calls</p>
                  </div>
                  <Switch
                    id="call-recording"
                    checked={twilioSettings.callRecording}
                    onCheckedChange={(checked) => handleSettingsChange('callRecording', checked)}
                  />
                </div>
                
                {twilioSettings.callRecording && (
                  <div className="flex items-center justify-between ml-6">
                    <div className="space-y-0.5">
                      <Label htmlFor="recording-consent">Recording Consent Message</Label>
                      <p className="text-xs text-gray-500">Play a message informing callers they are being recorded</p>
                    </div>
                    <Switch
                      id="recording-consent"
                      checked={twilioSettings.recordingConsent}
                      onCheckedChange={(checked) => handleSettingsChange('recordingConsent', checked)}
                    />
                  </div>
                )}
                
                {twilioSettings.callRecording && (
                  <div className="bg-yellow-50 p-4 rounded-md border border-yellow-200">
                    <div className="flex items-start">
                      <AlertTriangle className="text-yellow-500 mr-3 mt-0.5" size={18} />
                      <div>
                        <h4 className="font-medium text-yellow-800">Call Recording Compliance</h4>
                        <p className="text-sm text-yellow-700 mt-1">
                          Call recording may be subject to legal requirements in your jurisdiction. 
                          Always ensure you have proper consent from callers and comply with local regulations.
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="webhooks">
          <Card>
            <CardHeader>
              <CardTitle>Webhook Configuration</CardTitle>
              <CardDescription>Configure endpoints that Twilio will call during different call events</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="webhook-url">Primary Webhook URL</Label>
                <Input 
                  id="webhook-url" 
                  value={twilioSettings.webhookUrl}
                  onChange={(e) => handleSettingsChange('webhookUrl', e.target.value)}
                  placeholder="https://your-app.com/api/twilio/webhook"
                />
                <p className="text-xs text-gray-500">The main URL Twilio will call for incoming calls and messages</p>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="callback-url">Status Callback URL</Label>
                <Input 
                  id="callback-url" 
                  value={twilioSettings.callbackUrl}
                  onChange={(e) => handleSettingsChange('callbackUrl', e.target.value)}
                  placeholder="https://your-app.com/api/twilio/callback"
                />
                <p className="text-xs text-gray-500">URL to notify when call status changes (initiated, ringing, answered, completed)</p>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="fallback-url">Fallback URL</Label>
                <Input 
                  id="fallback-url" 
                  value={twilioSettings.fallbackUrl}
                  onChange={(e) => handleSettingsChange('fallbackUrl', e.target.value)}
                  placeholder="https://your-app.com/api/twilio/fallback"
                />
                <p className="text-xs text-gray-500">URL to call if the primary webhook fails or times out</p>
              </div>
              
              <div className="bg-blue-50 p-4 rounded-md border border-blue-200">
                <div className="flex items-start">
                  <Shield className="text-blue-500 mr-3 mt-0.5" size={18} />
                  <div>
                    <h4 className="font-medium text-blue-800">Webhook Security</h4>
                    <p className="text-sm text-blue-700 mt-1">
                      Your webhooks should be secured to prevent unauthorized access. 
                      The system validates all incoming Twilio requests using signature verification.
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="logging">
          <Card>
            <CardHeader>
              <div className="flex justify-between items-center">
                <div>
                  <CardTitle>Call Logs</CardTitle>
                  <CardDescription>Recent call activity from Twilio</CardDescription>
                </div>
                <Button variant="outline">Export Logs</Button>
              </div>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Timestamp</TableHead>
                    <TableHead>Direction</TableHead>
                    <TableHead>From</TableHead>
                    <TableHead>To</TableHead>
                    <TableHead>Duration</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Cost</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {callLogs.map(log => (
                    <TableRow key={log.id}>
                      <TableCell>{log.timestamp}</TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={`${log.direction === 'inbound' ? 'border-green-500 text-green-700' : 'border-blue-500 text-blue-700'}`}
                        >
                          {log.direction}
                        </Badge>
                      </TableCell>
                      <TableCell>{log.from}</TableCell>
                      <TableCell>{log.to}</TableCell>
                      <TableCell>{Math.floor(log.duration / 60)}:{(log.duration % 60).toString().padStart(2, '0')}</TableCell>
                      <TableCell>
                        <Badge
                          className={log.status === 'completed' ? 'bg-green-500' : 'bg-red-500'}
                        >
                          {log.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">${log.cost.toFixed(4)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
            <CardFooter className="flex justify-between">
              <div className="text-sm text-gray-500">
                Showing 3 of 243 calls
              </div>
              <div className="flex space-x-2">
                <Button variant="outline" size="sm" disabled>Previous</Button>
                <Button variant="outline" size="sm">Next</Button>
              </div>
            </CardFooter>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default TwilioIntegration;