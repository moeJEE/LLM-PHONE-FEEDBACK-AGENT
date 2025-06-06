import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Trash, 
  FileText, 
  Upload, 
  CheckCircle, 
  AlertCircle, 
  Search,
  RefreshCw,
  X,
  MoreHorizontal,
  Download,
  Eye,
  Loader2
} from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { 
  Dialog, 
  DialogContent, 
  DialogFooter, 
  DialogHeader, 
  DialogTitle 
} from '@/components/ui/dialog';
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuItem, 
  DropdownMenuTrigger,
  DropdownMenuSeparator
} from '@/components/ui/dropdown-menu';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';

// Skeleton Components for KnowledgeManagement
const DocumentListSkeleton = () => (
  <div className="space-y-4">
    {[1, 2, 3, 4, 5].map(i => (
      <Card key={i} className="p-4">
        <div className="flex items-start justify-between">
          <div className="flex items-start space-x-3 flex-1">
            <Skeleton className="h-8 w-8 rounded" />
            <div className="flex-1">
              <Skeleton className="h-5 w-64 mb-2" />
              <div className="flex items-center space-x-4">
                <Skeleton className="h-3 w-20" />
                <Skeleton className="h-3 w-16" />
                <Skeleton className="h-3 w-24" />
              </div>
              <div className="flex items-center space-x-2 mt-2">
                <Skeleton className="h-5 w-16" />
                <Skeleton className="h-5 w-12" />
              </div>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <Skeleton className="h-8 w-8 rounded" />
            <Skeleton className="h-8 w-8 rounded" />
          </div>
        </div>
      </Card>
    ))}
  </div>
);

const StatsSkeleton = () => (
  <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
    {[1, 2, 3, 4].map(i => (
      <Card key={i}>
        <CardContent className="p-4">
          <div className="flex items-center space-x-3">
            <Skeleton className="h-8 w-8 rounded" />
            <div className="flex-1">
              <Skeleton className="h-4 w-16 mb-1" />
              <Skeleton className="h-6 w-12" />
            </div>
          </div>
        </CardContent>
      </Card>
    ))}
  </div>
);

const ActivitySkeleton = () => (
  <div className="space-y-3">
    {[1, 2, 3, 4].map(i => (
      <div key={i} className="flex items-center space-x-3 p-3 border rounded-md">
        <Skeleton className="h-6 w-6 rounded" />
        <div className="flex-1">
          <Skeleton className="h-4 w-48 mb-1" />
          <Skeleton className="h-3 w-32" />
        </div>
        <Skeleton className="h-3 w-16" />
      </div>
    ))}
  </div>
);

const KnowledgeManagement = () => {
  const { getToken } = useAuth();
  
  // API Configuration
  const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api';
  
  // Loading states
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  
  // Helper function to make authenticated API calls
  const makeAuthenticatedRequest = useCallback(async (url, options = {}) => {
    try {
      let token = null;
      
      // Only get token if user is signed in (not in debug mode)
      try {
        token = await getToken();
      } catch (error) {
        // In debug mode or when not authenticated, proceed without token
      }
      
      const headers = {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` }),
        ...options.headers,
      };
      
      const response = await fetch(url, {
        ...options,
        headers,
      });
      
      if (!response.ok) {
        let errorText;
        try {
          const errorData = await response.json();
          errorText = errorData.detail || errorData.message || `HTTP ${response.status}`;
        } catch {
          errorText = await response.text() || `HTTP ${response.status}`;
        }
        throw new Error(errorText);
      }
      
      return response;
    } catch (error) {
      throw error;
    }
  }, [getToken]);

  // State management
  const [documents, setDocuments] = useState([]);
  const [uploadStatus, setUploadStatus] = useState('idle');
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [processingStatus, setProcessingStatus] = useState({
    total: 0,
    processed: 0,
    failed: 0,
    processing: 0
  });
  const [activeTab, setActiveTab] = useState('documents');
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [documentToDelete, setDocumentToDelete] = useState(null);
  const [isViewDocumentOpen, setIsViewDocumentOpen] = useState(false);
  const [toast, setToast] = useState({ visible: false, title: '', description: '', type: 'default' });
  const [recentActivities, setRecentActivities] = useState([]);
  const [error, setError] = useState(null);

  const fileInputRef = useRef(null);

  // Toast notification helper
  const showToast = useCallback((title, description, type = 'default') => {
    setToast({ visible: true, title, description, type });
    setTimeout(() => {
      setToast({ visible: false, title: '', description: '', type: 'default' });
    }, 5000);
  }, []);

  // Fetch documents from backend
  const fetchDocuments = useCallback(async (refresh = false) => {
    try {
      if (refresh) {
        setIsRefreshing(true);
      } else {
        setIsLoading(true);
      }
      setError(null);
      
      const response = await makeAuthenticatedRequest(`${API_BASE_URL}/knowledge/`);
      const documentsData = await response.json();
      
      // Transform backend data to match component expectations
      const transformedDocuments = documentsData.map(doc => ({
        id: doc.id,
        name: doc.name,
        status: doc.status, // processed, processing, failed
        size: doc.file_size ? formatFileSize(doc.file_size) : 'Unknown',
        uploadDate: formatDate(doc.created_at),
        pages: doc.page_count || 0,
        type: doc.document_type,
        tags: doc.tags || [],
        description: doc.description || '',
        error: doc.error_message || null,
        processed_at: doc.processed_at ? formatDate(doc.processed_at) : null,
        embeddings_count: doc.embeddings_count || 0
      }));
      
      setDocuments(transformedDocuments);
      
      // Calculate processing status
      const statusCount = transformedDocuments.reduce((acc, doc) => {
        acc[doc.status] = (acc[doc.status] || 0) + 1;
        return acc;
      }, {});
      
      setProcessingStatus({
        total: transformedDocuments.length,
        processed: statusCount.processed || 0,
        processing: statusCount.processing || 0,
        failed: statusCount.failed || 0
      });
      
      // Mock recent activities (this could be a separate API endpoint)
      const activities = transformedDocuments
        .slice(0, 5)
        .map((doc, index) => ({
          id: index + 1,
          type: doc.status === 'failed' ? 'error' : 
                doc.status === 'processing' ? 'process' : 'upload',
          documentName: doc.name,
          user: 'Current User',
          date: doc.uploadDate
        }));
      
      setRecentActivities(activities);
      
      if (refresh) {
        showToast('Success', 'Documents refreshed successfully', 'success');
      }
      
    } catch (error) {
      setError('Failed to load documents. Please try again.');
      showToast(
        "Error", 
        "Failed to load documents. Please try again.", 
        "error"
      );
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [getToken, makeAuthenticatedRequest, showToast]);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  // Show toast notification
  const showToastNotification = (title, description, type = 'default') => {
    setToast({ visible: true, title, description, type });
    setTimeout(() => {
      setToast({ visible: false, title: '', description: '', type: 'default' });
    }, 3000);
  };

  // Handle file upload
  const handleFileUpload = async (files) => {
    if (!files || files.length === 0) return;

    try {
      const token = await getToken();
      if (!token) {
        // User is not authenticated, cannot upload
        showToast("Error", "You must be signed in to upload documents", "error");
        return;
      }
    } catch {
      showToast("Error", "Authentication required to upload documents", "error");
      return;
    }

    const newUploads = [];
    setIsUploading(true);

    try {
      for (const file of files) {
        const fileId = `upload-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        
        const uploadData = {
          id: fileId,
          name: file.name,
          type: getFileType(file.name),
          status: 'uploading',
          uploadDate: new Date().toISOString(),
          lastUpdated: new Date().toISOString(),
          size: file.size,
          progress: 0
        };
        
        newUploads.push(uploadData);
        setDocuments(prev => [...prev, uploadData]);

        // Upload file
        const formData = new FormData();
        formData.append('file', file);
        formData.append('document_type', getFileType(file.name));
        formData.append('tags', JSON.stringify([]));
        
        try {
          const response = await makeAuthenticatedRequest(`${API_BASE_URL}/knowledge/upload`, {
            method: 'POST',
            body: formData,
            headers: {
              // Remove Content-Type to let browser set boundary for FormData
            }
          });
          
          const uploadedDoc = await response.json();
          
          // Update the document in the list
          setDocuments(prev => prev.map(doc => 
            doc.id === fileId ? {
              ...doc,
              id: uploadedDoc.id,
              status: 'processed',
              progress: 100,
              fileUrl: uploadedDoc.file_url || '#',
              metadata: uploadedDoc.metadata || {}
            } : doc
          ));
          
        } catch (uploadError) {
          // Update status to failed
          setDocuments(prev => prev.map(doc => 
            doc.id === fileId ? {
              ...doc,
              status: 'failed',
              progress: 0
            } : doc
          ));
          throw uploadError;
        }
      }
      
      showToast("Success", `${files.length} file(s) uploaded successfully`, "success");
      
    } catch (error) {
      showToast("Error", `Failed to upload files: ${error.message}`, "error");
    } finally {
      setIsUploading(false);
    }
  };
  
  const triggerFileInput = () => {
    if (fileInputRef.current && !isUploading) {
      fileInputRef.current.click();
    }
  };

  // Handle document deletion
  const confirmDeleteDocument = (doc) => {
    setDocumentToDelete(doc);
    setIsDeleteDialogOpen(true);
  };
  
  const handleDocumentDelete = async () => {
    if (!documentToDelete) return;
    
    setIsDeleting(true);
    
    try {
      const response = await makeAuthenticatedRequest(
        `${API_BASE_URL}/knowledge/${documentToDelete.id}`,
        { method: 'DELETE' }
      );
      
      // Remove document from local state
      setDocuments(prev => prev.filter(doc => doc.id !== documentToDelete.id));
      
      // Update processing status
      setProcessingStatus(prev => ({
        ...prev,
        total: prev.total - 1,
        [documentToDelete.status]: Math.max(0, prev[documentToDelete.status] - 1)
      }));
      
      showToast(
        'Document Deleted', 
        `"${documentToDelete.name}" has been deleted successfully.`, 
        'success'
      );
      
      // Refresh documents list
      await fetchDocuments(true);
      
    } catch (error) {
      showToast(
        'Delete Failed', 
        error.message || 'Failed to delete document. Please try again.', 
        'error'
      );
    } finally {
      setIsDeleting(false);
      setIsDeleteDialogOpen(false);
      setDocumentToDelete(null);
    }
  };

  // Handle view document details
  const handleViewDocument = async (doc) => {
    setSelectedDocument(doc);
    setIsViewDocumentOpen(true);
    
    try {
      const response = await makeAuthenticatedRequest(`${API_BASE_URL}/knowledge/${doc.id}`);
      const documentDetails = await response.json();
      setSelectedDocument(prev => ({ ...prev, ...documentDetails }));
    } catch (error) {
      showToast("Error", `Failed to fetch document details: ${error.message}`, "error");
    }
  };

  // Helper function to format file size
  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Helper function to format date
  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  // Filter documents
  const getFilteredDocuments = () => {
    return documents.filter(doc => {
      // Filter by search query
      const matchesSearch = doc.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                           (doc.tags && doc.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase())));
      
      // Filter by status
      const matchesStatus = filterStatus === 'all' || doc.status === filterStatus;
      
      return matchesSearch && matchesStatus;
    });
  };

  // Document Item component
  const DocumentItem = ({ document }) => (
    <div className="flex items-center justify-between p-4 border-b border-gray-200 hover:bg-gray-50">
      <div className="flex items-center space-x-3">
        <div className={`p-2 rounded-lg ${
          document.type === 'pdf' ? 'bg-red-100' : 
          document.type === 'docx' ? 'bg-blue-100' :
          document.type === 'txt' ? 'bg-green-100' :
          document.type === 'csv' ? 'bg-yellow-100' : 'bg-gray-100'
        }`}>
          <FileText size={20} className={`${
            document.type === 'pdf' ? 'text-red-600' : 
            document.type === 'docx' ? 'text-blue-600' :
            document.type === 'txt' ? 'text-green-600' :
            document.type === 'csv' ? 'text-yellow-600' : 'text-gray-600'
          }`} />
        </div>
        <div>
          <h3 className="font-medium">{document.name}</h3>
          <div className="flex items-center text-sm text-gray-500 space-x-2">
            <span>{document.size}</span>
            <span>•</span>
            <span>{document.pages} pages</span>
            <span>•</span>
            <span>Uploaded: {document.uploadDate}</span>
          </div>
          {document.tags && document.tags.length > 0 && (
            <div className="flex mt-1 space-x-1">
              {document.tags.map((tag, index) => (
                <Badge key={index} variant="secondary" className="text-xs">{tag}</Badge>
              ))}
            </div>
          )}
        </div>
      </div>
      <div className="flex items-center space-x-3">
        {document.status === 'processed' ? (
          <Badge variant="outline" className="bg-green-100 text-green-800 border-green-300">
            <CheckCircle size={14} className="mr-1 text-green-600" />
            Processed
          </Badge>
        ) : document.status === 'processing' ? (
          <Badge variant="outline" className="bg-blue-100 text-blue-800 border-blue-300">
            <div className="w-3 h-3 mr-1 rounded-full border-2 border-t-transparent border-blue-500 animate-spin"></div>
            Processing
          </Badge>
        ) : (
          <Badge variant="outline" className="bg-red-100 text-red-800 border-red-300">
            <AlertCircle size={14} className="mr-1 text-red-600" />
            Failed
          </Badge>
        )}
        
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm">
              <MoreHorizontal size={16} />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => handleViewDocument(document)}>
              <Eye size={16} className="mr-2 text-gray-600" />
              View Details
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Download size={16} className="mr-2 text-gray-600" />
              Download
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => confirmDeleteDocument(document)} className="text-red-600">
              <Trash size={16} className="mr-2" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );

  // Activity Item component
  const ActivityItem = ({ activity }) => {
    let icon;
    let colorClass;
    
    switch (activity.type) {
      case 'upload':
        icon = <Upload size={16} className="text-blue-500" />;
        colorClass = 'text-blue-800 bg-blue-50';
        break;
      case 'process':
        icon = <CheckCircle size={16} className="text-green-500" />;
        colorClass = 'text-green-800 bg-green-50';
        break;
      case 'delete':
        icon = <Trash size={16} className="text-red-500" />;
        colorClass = 'text-red-800 bg-red-50';
        break;
      case 'error':
        icon = <AlertCircle size={16} className="text-red-500" />;
        colorClass = 'text-red-800 bg-red-50';
        break;
      default:
        icon = <FileText size={16} className="text-gray-500" />;
        colorClass = 'text-gray-800 bg-gray-50';
    }
    
    return (
      <div className={`px-4 py-3 flex items-start ${colorClass} rounded-md mb-2`}>
        <div className="mr-3 mt-0.5">{icon}</div>
        <div>
          <p className="font-medium">
            {activity.type === 'upload' && 'Document Uploaded'}
            {activity.type === 'process' && 'Processing Completed'}
            {activity.type === 'delete' && 'Document Deleted'}
            {activity.type === 'error' && 'Processing Failed'}
          </p>
          <p className="text-sm">{activity.documentName}</p>
          <div className="flex items-center mt-1 text-xs text-gray-600">
            <span>{activity.user}</span>
            <span className="mx-1">•</span>
            <span>{activity.date}</span>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="mx-auto max-w-6xl p-4">
      {/* Toast Notification */}
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
      
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Knowledge Base Management</h1>
        <Button 
          variant="outline" 
          onClick={() => fetchDocuments(true)} 
          disabled={isRefreshing || isLoading}
          className="flex items-center gap-2"
        >
          <RefreshCw size={16} className={isRefreshing ? "animate-spin" : ""} />
          {isRefreshing ? 'Refreshing...' : 'Refresh'}
        </Button>
      </div>
      
      {/* Loading state for initial load */}
      {isLoading ? (
        <div className="space-y-6">
          <StatsSkeleton />
          <Card>
            <CardHeader>
              <Skeleton className="h-6 w-48" />
              <div className="flex items-center justify-between mt-4">
                <div className="flex items-center space-x-2">
                  <Skeleton className="h-10 w-64" />
                  <Skeleton className="h-10 w-32" />
                </div>
                <Skeleton className="h-10 w-24" />
              </div>
            </CardHeader>
            <CardContent>
              <DocumentListSkeleton />
            </CardContent>
          </Card>
        </div>
      ) : (
        <>
          {/* Updated Tabs as a controlled component */}
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="documents">Documents</TabsTrigger>
              <TabsTrigger value="upload">Upload</TabsTrigger>
              <TabsTrigger value="settings">Settings</TabsTrigger>
            </TabsList>
            
            {/* Documents Tab */}
            <TabsContent value="documents">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    Knowledge Base Documents
                    {isRefreshing && (
                      <RefreshCw size={16} className="animate-spin text-blue-500" />
                    )}
                  </CardTitle>
                  <div className="flex items-center justify-between mt-4">
                    <div className="flex items-center space-x-2 w-full max-w-md">
                      <div className="relative w-full">
                        <Search size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
                        <Input
                          placeholder="Search documents..."
                          className="pl-9 w-full"
                          value={searchQuery}
                          onChange={(e) => setSearchQuery(e.target.value)}
                          disabled={isRefreshing}
                        />
                        {searchQuery && (
                          <button 
                            className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                            onClick={() => setSearchQuery('')}
                          >
                            <X size={14} />
                          </button>
                        )}
                      </div>
                      <Select 
                        value={filterStatus} 
                        onValueChange={setFilterStatus}
                        disabled={isRefreshing}
                      >
                        <SelectTrigger className="w-[180px]">
                          <SelectValue placeholder="Filter by status" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Status</SelectItem>
                          <SelectItem value="processed">Processed</SelectItem>
                          <SelectItem value="processing">Processing</SelectItem>
                          <SelectItem value="failed">Failed</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <Button 
                      onClick={() => setActiveTab('upload')}
                      className="bg-blue-600 flex items-center"
                      type="button"
                      disabled={isRefreshing}
                    >
                      <Upload size={16} className="mr-2" />
                      Upload
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  {isRefreshing ? (
                    <StatsSkeleton />
                  ) : (
                    <div className="mb-6 grid grid-cols-4 gap-4">
                      <Card className="p-4 text-center">
                        <h3 className="text-xl font-bold text-blue-500">{processingStatus.total || 0}</h3>
                        <p className="text-sm text-gray-500">Total Documents</p>
                      </Card>
                      <Card className="p-4 text-center">
                        <h3 className="text-xl font-bold text-green-500">{processingStatus.processed || 0}</h3>
                        <p className="text-sm text-gray-500">Processed</p>
                      </Card>
                      <Card className="p-4 text-center">
                        <h3 className="text-xl font-bold text-yellow-500">{processingStatus.processing || 0}</h3>
                        <p className="text-sm text-gray-500">Processing</p>
                      </Card>
                      <Card className="p-4 text-center">
                        <h3 className="text-xl font-bold text-red-500">{processingStatus.failed || 0}</h3>
                        <p className="text-sm text-gray-500">Failed</p>
                      </Card>
                    </div>
                  )}
                  
                  <div className="border rounded-md">
                    {isRefreshing ? (
                      <DocumentListSkeleton />
                    ) : getFilteredDocuments().length > 0 ? (
                      getFilteredDocuments().map(doc => <DocumentItem key={doc.id} document={doc} />)
                    ) : (
                      <div className="p-8 text-center text-gray-500">
                        {documents.length > 0 
                          ? 'No documents match your search criteria.'
                          : 'No documents in knowledge base. Upload documents to get started.'}
                      </div>
                    )}
                  </div>
                  
                  <div className="mt-4 text-sm text-gray-500">
                    Showing {getFilteredDocuments().length} of {documents.length} documents
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
            
            {/* Upload Tab */}
            <TabsContent value="upload">
              <Card>
                <CardHeader>
                  <CardTitle>Upload Documents</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="p-6 border-2 border-dashed rounded-md border-gray-300 text-center">
                    <div className="mb-4">
                      {isUploading ? (
                        <Loader2 size={40} className="mx-auto text-blue-500 animate-spin" />
                      ) : (
                        <Upload size={40} className="mx-auto text-gray-400" />
                      )}
                      <h3 className="mt-2 text-lg">
                        {isUploading ? 'Uploading documents...' : 'Upload your documents'}
                      </h3>
                      <p className="text-sm text-gray-500">
                        {isUploading ? 'Please wait while your files are being processed' : 'Supported formats: PDF, DOCX, TXT, CSV'}
                      </p>
                    </div>
                    
                    <input
                      type="file"
                      ref={fileInputRef}
                      onChange={handleFileUpload}
                      className="hidden"
                      multiple
                      accept=".pdf,.docx,.txt,.csv"
                      disabled={isUploading}
                    />
                    
                    <Button 
                      className="bg-blue-500" 
                      onClick={triggerFileInput}
                      type="button"
                      disabled={isUploading}
                    >
                      {isUploading ? (
                        <>
                          <Loader2 size={16} className="mr-2 animate-spin" />
                          Uploading...
                        </>
                      ) : (
                        <>
                          <Upload size={16} className="mr-2" />
                          Select Files
                        </>
                      )}
                    </Button>
                    
                    {uploadStatus === 'uploading' && (
                      <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-md">
                        <div className="flex items-center justify-center">
                          <Loader2 size={16} className="mr-2 animate-spin text-blue-500" />
                          <span className="text-blue-700">Processing your files...</span>
                        </div>
                      </div>
                    )}
                    
                    {uploadStatus === 'success' && (
                      <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-md">
                        <div className="flex items-center justify-center">
                          <CheckCircle size={16} className="mr-2 text-green-500" />
                          <span className="text-green-700">Files uploaded successfully!</span>
                        </div>
                      </div>
                    )}
                    
                    {uploadStatus === 'error' && (
                      <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-md">
                        <div className="flex items-center justify-center">
                          <AlertCircle size={16} className="mr-2 text-red-500" />
                          <span className="text-red-700">Upload failed. Please try again.</span>
                        </div>
                      </div>
                    )}
                  </div>
                  
                  {/* Recent Activity */}
                  <div className="mt-8">
                    <h3 className="text-lg font-medium mb-4">Recent Activity</h3>
                    {isRefreshing ? (
                      <ActivitySkeleton />
                    ) : recentActivities.length > 0 ? (
                      recentActivities.map(activity => (
                        <ActivityItem key={activity.id} activity={activity} />
                      ))
                    ) : (
                      <div className="text-center py-8 text-gray-500">
                        No recent activity
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
            
            {/* Settings Tab */}
            <TabsContent value="settings">
              <Card>
                <CardHeader>
                  <CardTitle>Knowledge Base Settings</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-6">
                    <div>
                      <Label>Auto-process uploaded documents</Label>
                      <div className="flex items-center space-x-2 mt-2">
                        <Switch defaultChecked={true} />
                        <span className="text-sm text-gray-500">
                          Automatically process documents after upload
                        </span>
                      </div>
                    </div>
                    
                    <Separator />
                    
                    <div>
                      <Label>Maximum file size (MB)</Label>
                      <Input 
                        type="number" 
                        defaultValue="50" 
                        className="mt-2 w-32"
                        min="1"
                        max="100"
                      />
                    </div>
                    
                    <Separator />
                    
                    <div>
                      <Label>Allowed file types</Label>
                      <div className="mt-2 space-y-2">
                        <div className="flex items-center space-x-2">
                          <input type="checkbox" defaultChecked id="pdf" />
                          <Label htmlFor="pdf">PDF</Label>
                        </div>
                        <div className="flex items-center space-x-2">
                          <input type="checkbox" defaultChecked id="docx" />
                          <Label htmlFor="docx">DOCX</Label>
                        </div>
                        <div className="flex items-center space-x-2">
                          <input type="checkbox" defaultChecked id="txt" />
                          <Label htmlFor="txt">TXT</Label>
                        </div>
                        <div className="flex items-center space-x-2">
                          <input type="checkbox" defaultChecked id="csv" />
                          <Label htmlFor="csv">CSV</Label>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </>
      )}
      
      {/* Delete Confirmation Dialog */}
      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Document</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm text-gray-600">
              Are you sure you want to delete "{documentToDelete?.name}"? This action cannot be undone.
            </p>
          </div>
          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => {
                setIsDeleteDialogOpen(false);
                setDocumentToDelete(null);
              }}
              disabled={isDeleting}
            >
              Cancel
            </Button>
            <Button 
              variant="destructive" 
              onClick={handleDocumentDelete}
              disabled={isDeleting}
            >
              {isDeleting ? (
                <>
                  <Loader2 size={16} className="mr-2 animate-spin" />
                  Deleting...
                </>
              ) : (
                'Delete'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default KnowledgeManagement;
