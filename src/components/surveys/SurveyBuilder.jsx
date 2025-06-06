import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { 
  Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter 
} from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { 
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger 
} from '@/components/ui/dialog';
import { 
  PlusCircle, Trash2, Copy, ArrowUpDown, ChevronDown, ChevronUp, Settings, Save, 
  PlayCircle, ArrowUp, ArrowDown, Pencil, AlertTriangle, LayoutGrid, ArrowRight, 
  Check, X, ExternalLink, Phone, MoreHorizontal, MessageSquare, Plus, ArrowLeft, 
  RefreshCw, Loader2
} from 'lucide-react';
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Table, TableBody, TableCell, TableHeader, TableRow, TableHead
} from "@/components/ui/table";
import { v4 as uuidv4 } from 'uuid';

// Skeleton Components for SurveyBuilder
const SurveyListSkeleton = () => (
  <div className="space-y-4">
    {[1, 2, 3, 4, 5].map(i => (
      <Card key={i} className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <Skeleton className="h-5 w-48 mb-2" />
            <Skeleton className="h-3 w-32 mb-1" />
            <Skeleton className="h-3 w-24" />
          </div>
          <div className="flex items-center space-x-2">
            <Skeleton className="h-6 w-16" />
            <Skeleton className="h-8 w-8 rounded" />
          </div>
        </div>
      </Card>
    ))}
  </div>
);

const QuestionCardSkeleton = () => (
  <Card className="mb-4">
    <CardHeader>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <Skeleton className="h-5 w-64 mb-2" />
          <Skeleton className="h-4 w-32" />
        </div>
        <div className="flex items-center space-x-2">
          <Skeleton className="h-8 w-16" />
          <Skeleton className="h-8 w-8 rounded" />
        </div>
      </div>
    </CardHeader>
    <CardContent>
      <div className="space-y-3">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
        <div className="grid grid-cols-2 gap-2">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
        </div>
      </div>
    </CardContent>
  </Card>
);

const SurveySettingsSkeleton = () => (
  <div className="space-y-6">
    <Card>
      <CardHeader>
        <Skeleton className="h-6 w-32" />
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Skeleton className="h-4 w-16 mb-2" />
            <Skeleton className="h-10 w-full" />
          </div>
          <div>
            <Skeleton className="h-4 w-20 mb-2" />
            <Skeleton className="h-10 w-full" />
          </div>
        </div>
        <div>
          <Skeleton className="h-4 w-24 mb-2" />
          <Skeleton className="h-20 w-full" />
        </div>
      </CardContent>
    </Card>
    
    <Card>
      <CardHeader>
        <Skeleton className="h-6 w-28" />
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-3 gap-4">
          <div>
            <Skeleton className="h-4 w-16 mb-2" />
            <Skeleton className="h-10 w-full" />
          </div>
          <div>
            <Skeleton className="h-4 w-20 mb-2" />
            <Skeleton className="h-10 w-full" />
          </div>
          <div>
            <Skeleton className="h-4 w-24 mb-2" />
            <Skeleton className="h-10 w-full" />
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
);

const SurveyBuilder = () => {
  const { getToken, isSignedIn, user } = useAuth();
  
  // API Configuration
  const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
  
  // Loading states
  const [isLoading, setIsLoading] = useState(true);
  const [isSurveyLoading, setIsSurveyLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [isSwitchingSurvey, setIsSwitchingSurvey] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  
  // Helper function to make authenticated API calls
  const authToken = useCallback(async () => {
    try {
      if (isSignedIn && user) {
        const freshToken = await getToken();
        return freshToken;
      }
      return null;
    } catch (error) {
      return null;
    }
  }, [isSignedIn, user, getToken]);

  // Existing state for survey management
  const [currentSurvey, setCurrentSurvey] = useState({
    id: null,
    title: '',
    description: '',
    intro_message: 'Welcome to our survey. Thank you for participating.',
    outro_message: 'Thank you for completing the survey!',
    voice_type: 'neutral_female',
    voice_speed: 'normal',
    max_duration: 10,
    max_retries: 3,
    call_during_business_hours: true,
    avoid_weekends: true,
    respect_timezone: true,
    status: 'draft',
    questions: []
  });
  
  const [allSurveys, setAllSurveys] = useState([]);
  const [expandedQuestion, setExpandedQuestion] = useState(null);
  const [activeTab, setActiveTab] = useState('all-surveys');
  const [isLogicDialogOpen, setIsLogicDialogOpen] = useState(false);
  const [selectedQuestionForLogic, setSelectedQuestionForLogic] = useState(null);
  const [showTestConfirmation, setShowTestConfirmation] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const [showToast, setShowToast] = useState({ visible: false, message: '', type: '' });
  
  // ***** New State for Creating a Survey *****
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [newSurveyTitle, setNewSurveyTitle] = useState('');
  const [newSurveyDescription, setNewSurveyDescription] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState('blank');
  
  // Toast notification helper
  const showToastMessage = useCallback((message, type = 'info') => {
    setShowToast({ visible: true, message, type });
    setTimeout(() => {
      setShowToast({ visible: false, message: '', type: '' });
    }, 5000);
  }, []);
  
  // ***** Updated to fetch real data from backend *****
  const loadSurveys = useCallback(async () => {
    try {
      setIsLoading(true);
      
      const token = await authToken();
      
      if (!token) {
        // User is not authenticated
        setAllSurveys([]);
        return;
      }

      // Proceed with authenticated request
      const response = await fetch(`${API_BASE_URL}/api/surveys/?limit=50`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      const surveys = await response.json();
      setAllSurveys(surveys);
      
      if (surveys.length === 0) {
        // No surveys returned
        try {
          const debugResponse = await fetch(`${API_BASE_URL}/api/surveys/?limit=5&debug=true`, {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          });
          const debugSurveys = await debugResponse.json();
          
          setAllSurveys(debugSurveys);
        } catch (debugError) {
          // Debug request failed
        }
      }

    } catch (error) {
      showToastMessage(`Failed to load surveys: ${error.message}`, 'error');
    } finally {
      setIsLoading(false);
    }
  }, [authToken]);
  
  const loadSurvey = useCallback(async (surveyId) => {
    try {
      const token = await authToken();
      const response = await fetch(`${API_BASE_URL}/api/surveys/${surveyId}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      const survey = await response.json();
      
      setCurrentSurvey({
        id: survey.id,
        title: survey.title,
        description: survey.description || '',
        intro_message: survey.intro_message || 'Welcome to our survey. Thank you for participating.',
        outro_message: survey.outro_message || 'Thank you for completing the survey!',
        voice_type: survey.voice_type || 'neutral_female',
        voice_speed: survey.voice_speed || 'normal',
        max_duration: survey.max_duration || 10,
        max_retries: survey.max_retries || 3,
        call_during_business_hours: survey.call_during_business_hours ?? true,
        avoid_weekends: survey.avoid_weekends ?? true,
        respect_timezone: survey.respect_timezone ?? true,
        status: survey.status || 'draft',
        questions: survey.questions || []
      });
      setIsDirty(false);
      return survey;
    } catch (error) {
      throw new Error('Failed to load survey. Please try again.');
    }
  }, [authToken]);
  
  // ***** Updated saveSurvey to actually save to backend *****
  const saveSurvey = useCallback(async (surveyData) => {
    setIsSaving(true);
    try {
      const token = await authToken();
      
      let response;
      
      if (currentSurvey?.id) {
        // Update existing survey
        response = await fetch(`${API_BASE_URL}/api/surveys/${currentSurvey.id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify(surveyData),
        });
      } else {
        // Create new survey
        response = await fetch(`${API_BASE_URL}/api/surveys/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify(surveyData),
        });
      }
      
      const savedSurvey = await response.json();
      
      showToastMessage('Survey saved successfully', 'success');
      setIsDirty(false);
      
      // Refresh the surveys list
      await loadSurveys();
      
      return savedSurvey;
    } catch (error) {
      throw new Error('Failed to save survey. Please try again.');
    } finally {
      setIsSaving(false);
    }
  }, [authToken, currentSurvey?.id, showToastMessage, loadSurveys]);
  
  const addQuestion = () => {
    const newId = `q${currentSurvey.questions.length + 1}_new`;
    const newQuestion = {
      id: newId,
      text: 'New Question',
      voice_prompt: 'New Question',
      question_type: 'open_ended',
      required: true,
      options: [],
      follow_up_logic: {}
    };
    
    setCurrentSurvey(prev => ({
      ...prev,
      questions: [...prev.questions, newQuestion]
    }));
    setExpandedQuestion(newId);
    setIsDirty(true);
  };

  const updateQuestion = (questionId, updatedQuestion) => {
    setCurrentSurvey(prev => ({
      ...prev,
      questions: prev.questions.map(q => 
        q.id === questionId ? { ...q, ...updatedQuestion } : q
      )
    }));
    setIsDirty(true);
  };

  const deleteQuestion = (questionId) => {
    // Check if question is referenced in follow-up logic
    const hasReferences = currentSurvey.questions.some(q => {
      const logic = q.follow_up_logic || {};
      return Object.values(logic).includes(questionId);
    });
    
    if (hasReferences) {
      showToastMessage("This question is referenced in follow-up logic. Please update logic before removing.", 'error');
      return;
    }
    
    // Find the question being deleted
    const questionToDelete = currentSurvey.questions.find(q => q.id === questionId);
    if (!questionToDelete) {
      showToastMessage("Question not found - refresh the page and try again.", 'error');
      return;
    }
    
    setCurrentSurvey(prev => {
      const newQuestions = prev.questions.filter(q => q.id !== questionId);
      return {
        ...prev,
        questions: newQuestions
      };
    });
    
    // Close expanded question if it's the one being deleted
    if (expandedQuestion === questionId) {
      setExpandedQuestion(null);
    }
    
    setIsDirty(true);
    
    // Show success message
    showToastMessage("Question deleted successfully!", 'success');
  };

  const moveQuestion = (dragIndex, hoverIndex) => {
    const newQuestions = [...currentSurvey.questions];
    const draggedQuestion = newQuestions[dragIndex];
    newQuestions.splice(dragIndex, 1);
    newQuestions.splice(hoverIndex, 0, draggedQuestion);
    
    setCurrentSurvey(prev => ({
      ...prev,
      questions: newQuestions
    }));
    setIsDirty(true);
  };
  
  const openLogicDialog = (question) => {
    setSelectedQuestionForLogic(question);
    setIsLogicDialogOpen(true);
  };
  
  const handleUpdateLogic = (condition, targetQuestionId) => {
    if (!selectedQuestionForLogic) return;
    const updatedLogic = { ...selectedQuestionForLogic.follow_up_logic };
    if (!targetQuestionId) {
      delete updatedLogic[condition];
    } else {
      updatedLogic[condition] = targetQuestionId;
    }
    updateQuestion(selectedQuestionForLogic.id, { follow_up_logic: updatedLogic });
  };
  
  const toggleQuestionExpand = (id) => {
    setExpandedQuestion(expandedQuestion === id ? null : id);
  };
  
  // Question type options
  const questionTypes = [
    { value: 'open_ended', label: 'Open-ended (Text)' },
    { value: 'numeric', label: 'Numeric Rating (1-5)' },
    { value: 'yes_no', label: 'Yes/No' },
    { value: 'multiple_choice', label: 'Multiple Choice' }
  ];
  
  // Voice options
  const voiceTypes = [
    { value: 'neutral_female', label: 'Neutral Female' },
    { value: 'neutral_male', label: 'Neutral Male' },
    { value: 'professional_female', label: 'Professional Female' },
    { value: 'professional_male', label: 'Professional Male' },
    { value: 'friendly_female', label: 'Friendly Female' },
    { value: 'friendly_male', label: 'Friendly Male' }
  ];
  
  const speedOptions = [
    { value: 'slow', label: 'Slow' },
    { value: 'normal', label: 'Normal' },
    { value: 'fast', label: 'Fast' }
  ];
  
  // Helpers for logic
  const getLogicDescription = (condition, questionType) => {
    if (questionType === 'numeric') {
      return condition === '1-2' ? 'Rating 1-2 (Low)' :
             condition === '3' ? 'Rating 3 (Medium)' :
             condition === '4-5' ? 'Rating 4-5 (High)' : condition;
    } else if (questionType === 'yes_no') {
      return condition === 'yes' ? 'If Yes' : condition === 'no' ? 'If No' : condition;
    } else if (questionType === 'multiple_choice') {
      return `If "${condition}"`;
    }
    return condition;
  };
  
  const canHaveLogic = (questionType) => {
    return ['numeric', 'yes_no', 'multiple_choice'].includes(questionType);
  };
  
  const getLogicConditions = (questionType, options = []) => {
    if (questionType === 'numeric') {
      return [
        { value: '1-2', label: 'Rating 1-2 (Low)' },
        { value: '3', label: 'Rating 3 (Medium)' },
        { value: '4-5', label: 'Rating 4-5 (High)' }
      ];
    } else if (questionType === 'yes_no') {
      return [
        { value: 'yes', label: 'If Yes' },
        { value: 'no', label: 'If No' }
      ];
    } else if (questionType === 'multiple_choice') {
      return options.map(option => ({ value: option, label: `If "${option}"` }));
    }
    return [];
  };
  
  const QuestionCard = ({ question, index }) => {
    const isExpanded = expandedQuestion === question.id;
    const hasLogic = Object.keys(question.follow_up_logic).length > 0;
    
    return (
      <div className="mb-4">
        <Card>
          <CardHeader className="pb-2">
            <div className="flex justify-between items-center">
              <div className="flex items-center">
                <div className="flex flex-col mr-2">
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="p-1 h-6"
                    onClick={() => moveQuestion(index, index - 1)}
                    disabled={index === 0}
                  >
                    <ArrowUp size={14} className="text-gray-400" />
                  </Button>
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="p-1 h-6"
                    onClick={() => moveQuestion(index, index + 1)}
                    disabled={index === currentSurvey.questions.length - 1}
                  >
                    <ArrowDown size={14} className="text-gray-400" />
                  </Button>
                </div>
                <div>
                  <div className="flex items-center">
                    <Badge variant="outline" className="mr-2">Q{index + 1}</Badge>
                    <CardTitle className="text-base">
                      {question.text}
                    </CardTitle>
                  </div>
                  {!isExpanded && (
                    <div className="flex items-center mt-1 space-x-2">
                      <Badge variant={question.required ? "default" : "outline"} className="text-xs">
                        {question.required ? "Required" : "Optional"}
                      </Badge>
                      <Badge variant="secondary" className="text-xs">
                        {questionTypes.find(t => t.value === question.question_type)?.label || question.question_type}
                      </Badge>
                      {hasLogic && (
                        <Badge variant="secondary" className="text-xs bg-blue-100 text-blue-800 hover:bg-blue-200">
                          <Settings size={10} className="mr-1" />
                          Has Logic
                        </Badge>
                      )}
                    </div>
                  )}
                </div>
              </div>
              <div className="flex">
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={() => toggleQuestionExpand(question.id)}
                >
                  {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </Button>
              </div>
            </div>
          </CardHeader>
          
          {isExpanded && (
            <CardContent>
              <div className="space-y-4">
                <div>
                  <Label htmlFor={`question-text-${question.id}`} className="mb-1 block">Question Text</Label>
                  <Input
                    id={`question-text-${question.id}`}
                    value={question.text}
                    onChange={(e) => updateQuestion(question.id, { text: e.target.value })}
                  />
                </div>
                <div>
                  <Label htmlFor={`voice-prompt-${question.id}`} className="mb-1 block">
                    Voice Prompt (spoken version)
                  </Label>
                  <Textarea
                    id={`voice-prompt-${question.id}`}
                    rows={2}
                    value={question.voice_prompt}
                    onChange={(e) => updateQuestion(question.id, { voice_prompt: e.target.value })}
                  />
                </div>
                <div>
                  <Label htmlFor={`question-type-${question.id}`} className="mb-1 block">Question Type</Label>
                  <Select 
                    value={question.question_type}
                    onValueChange={(value) => updateQuestion(question.id, { question_type: value })}
                  >
                    <SelectTrigger id={`question-type-${question.id}`}>
                      <SelectValue placeholder="Select question type" />
                    </SelectTrigger>
                    <SelectContent>
                      {questionTypes.map(type => (
                        <SelectItem key={type.value} value={type.value}>{type.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                {question.question_type === 'multiple_choice' && (
                  <div>
                    <Label className="mb-1 block">Options</Label>
                    {question.options && question.options.length > 0 ? (
                      question.options.map((option, i) => (
                        <div key={i} className="flex mb-2">
                          <Input
                            className="rounded-r-none"
                            value={option}
                            onChange={(e) => {
                              const newOptions = [...question.options];
                              newOptions[i] = e.target.value;
                              updateQuestion(question.id, { options: newOptions });
                            }}
                          />
                          <Button
                            variant="outline"
                            size="icon"
                            className="rounded-l-none"
                            onClick={() => {
                              const newOptions = question.options.filter((_, idx) => idx !== i);
                              updateQuestion(question.id, { options: newOptions });
                            }}
                          >
                            <Trash2 size={16} />
                          </Button>
                        </div>
                      ))
                    ) : (
                      <div className="text-sm text-gray-500 italic mb-2">No options added yet</div>
                    )}
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={() => {
                        updateQuestion(
                          question.id, 
                          { options: [...(question.options || []), `Option ${(question.options || []).length + 1}`] }
                        );
                      }}
                    >
                      <PlusCircle size={16} className="mr-2" />
                      Add Option
                    </Button>
                  </div>
                )}
                
                <div className="flex items-center space-x-2">
                  <Switch
                    id={`required-${question.id}`}
                    checked={question.required}
                    onCheckedChange={(checked) => updateQuestion(question.id, { required: checked })}
                  />
                  <Label htmlFor={`required-${question.id}`}>Required question</Label>
                </div>
                
                {canHaveLogic(question.question_type) && (
                  <div className="border-t pt-4 mt-4">
                    <Label className="mb-1 block font-medium">Question Logic</Label>
                    {hasLogic ? (
                      <div className="space-y-2 mb-3">
                        {Object.entries(question.follow_up_logic).map(([condition, targetId]) => {
                          const targetQuestion = currentSurvey.questions.find(q => q.id === targetId);
                          return (
                            <div key={condition} className="flex items-center border rounded-md p-2 bg-blue-50">
                              <div className="flex-1">
                                <div className="text-sm font-medium">{getLogicDescription(condition, question.question_type)}</div>
                                <div className="flex items-center text-sm text-blue-700">
                                  <ArrowRight size={14} className="mr-1" />
                                  {targetQuestion ? 
                                    `Q${currentSurvey.questions.indexOf(targetQuestion) + 1}: ${targetQuestion.text.substring(0, 30)}${targetQuestion.text.length > 30 ? '...' : ''}` : 
                                    'Unknown question'}
                                </div>
                              </div>
                              <Button 
                                variant="ghost" 
                                size="sm"
                                className="text-red-500"
                                onClick={() => handleUpdateLogic(condition, null)}
                              >
                                <Trash2 size={14} />
                              </Button>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <div className="text-sm text-gray-500 mb-3 italic">No logic rules set yet</div>
                    )}
                    <Button 
                      variant="outline" 
                      size="sm" 
                      className="text-blue-600"
                      onClick={() => openLogicDialog(question)}
                    >
                      <Settings size={16} className="mr-2" />
                      {hasLogic ? 'Edit Logic' : 'Add Logic'}
                    </Button>
                  </div>
                )}
                
                <div className="flex space-x-2 pt-2 border-t mt-4">
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={() => {
                      const newId = `${question.id}_copy`;
                      const newQuestion = { ...question, id: newId };
                      const questions = [...currentSurvey.questions];
                      questions.splice(index + 1, 0, newQuestion);
                      setCurrentSurvey({ ...currentSurvey, questions });
                    }}
                  >
                    <Copy size={16} className="mr-2" />
                    Duplicate
                  </Button>
                  
                  <Button 
                    variant="outline" 
                    size="sm" 
                    className="text-red-600"
                    onClick={() => deleteQuestion(question.id)}
                  >
                    <Trash2 size={16} className="mr-2" />
                    Delete
                  </Button>
                </div>
              </div>
            </CardContent>
          )}
        </Card>
      </div>
    );
  };
  
  // ***** Updated function to handle survey selection from the table *****
  const handleSelectSurvey = async (surveyId) => {
    setIsSwitchingSurvey(true);
    
    // Clear current survey immediately to prevent showing old data
    setCurrentSurvey({
      id: null,
      title: '',
      description: '',
      intro_message: 'Welcome to our survey. Thank you for participating.',
      outro_message: 'Thank you for completing the survey!',
      voice_type: 'neutral_female',
      voice_speed: 'normal',
      max_duration: 10,
      max_retries: 3,
      call_during_business_hours: true,
      avoid_weekends: true,
      respect_timezone: true,
      status: 'draft',
      questions: []
    });
    
    // Reset dirty state
    setIsDirty(false);
    
    try {
      // Wait for survey to load completely before switching tabs
      await loadSurvey(surveyId);
      setActiveTab('builder');
    } catch (error) {
      // Stay on current tab if loading fails
    } finally {
      setIsSwitchingSurvey(false);
    }
  };
  
  // ***** New function to create new survey and switch to builder *****
  const handleCreateNewSurveyFromTab = () => {
    setIsCreateDialogOpen(true);
  };
  
  // ***** New function to handle "back to surveys" navigation *****
  const handleBackToSurveys = () => {
    setActiveTab('all-surveys');
  };
  
  // ***** Enhanced function to start editing with better UX *****
  const startEditingSurvey = async (surveyId) => {
    await handleSelectSurvey(surveyId);
  };
  
  // ***** Updated handleCreateNewSurvey to save to backend *****
  const handleCreateNewSurvey = async () => {
    if (!newSurveyTitle.trim()) {
      showToastMessage("Please enter a survey title", 'error');
      return;
    }
    
    setIsCreating(true);
    
    try {
      let newSurvey;
      if (selectedTemplate === 'blank') {
        newSurvey = {
          title: newSurveyTitle,
          description: newSurveyDescription,
          intro_message: 'Welcome to our survey. Thank you for participating.',
          outro_message: 'Thank you for completing the survey!',
          voice_type: 'neutral_female',
          voice_speed: 'normal',
          max_duration: 10,
          max_retries: 3,
          call_during_business_hours: true,
          avoid_weekends: true,
          respect_timezone: true,
          status: 'draft',
          questions: []
        };
      } else if (selectedTemplate === 'satisfaction') {
        newSurvey = {
          title: newSurveyTitle,
          description: newSurveyDescription,
          intro_message: 'Hello! Thank you for taking the time to participate in our brief satisfaction survey. Your feedback helps us improve our service.',
          outro_message: 'Thank you for your valuable feedback! We appreciate your time and will use your input to enhance our services.',
          voice_type: 'neutral_female',
          voice_speed: 'normal',
          max_duration: 10,
          max_retries: 3,
          call_during_business_hours: true,
          avoid_weekends: true,
          respect_timezone: true,
          status: 'draft',
          questions: [
            {
              id: 'q1',
              text: 'On a scale from 1 to 5, how satisfied are you with our service?',
              voice_prompt: 'On a scale from 1 to 5, where 1 is very dissatisfied and 5 is very satisfied, how would you rate our service?',
              question_type: 'numeric',
              required: true,
              options: [],
              follow_up_logic: {}
            },
            {
              id: 'q2',
              text: 'What aspects of our service do you appreciate the most?',
              voice_prompt: 'What aspects of our service do you appreciate the most?',
              question_type: 'open_ended',
              required: false,
              options: [],
              follow_up_logic: {}
            },
            {
              id: 'q3',
              text: 'Would you recommend our service to others?',
              voice_prompt: 'Would you recommend our service to friends or colleagues?',
              question_type: 'yes_no',
              required: true,
              options: [],
              follow_up_logic: {}
            }
          ]
        };
      } else if (selectedTemplate === 'feedback') {
        newSurvey = {
          title: newSurveyTitle,
          description: newSurveyDescription,
          intro_message: 'Hello! We value your feedback about our product. This brief survey will help us improve.',
          outro_message: 'Thank you for your feedback! Your input is valuable to our product development.',
          voice_type: 'neutral_female',
          voice_speed: 'normal',
          max_duration: 10,
          max_retries: 3,
          call_during_business_hours: true,
          avoid_weekends: true,
          respect_timezone: true,
          status: 'draft',
          questions: [
            {
              id: 'q1',
              text: 'How would you rate the ease of use of our product?',
              voice_prompt: 'On a scale from 1 to 5, how would you rate the ease of use of our product?',
              question_type: 'numeric',
              required: true,
              options: [],
              follow_up_logic: {}
            },
            {
              id: 'q2',
              text: 'Which features do you find most useful?',
              voice_prompt: 'Which features of our product do you find most useful?',
              question_type: 'open_ended',
              required: true,
              options: [],
              follow_up_logic: {}
            },
            {
              id: 'q3',
              text: 'What improvements would you suggest for our product?',
              voice_prompt: 'What improvements would you suggest for our product?',
              question_type: 'open_ended',
              required: false,
              options: [],
              follow_up_logic: {}
            }
          ]
        };
      }
      
      // Create survey via API
      const response = await fetch(`${API_BASE_URL}/api/surveys/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${await authToken()}`,
        },
        body: JSON.stringify(newSurvey),
      });
      
      const createdSurvey = await response.json();
      
      // Set as current survey
      setCurrentSurvey({
        id: createdSurvey.id,
        title: createdSurvey.title,
        description: createdSurvey.description || '',
        intro_message: createdSurvey.intro_message || 'Welcome to our survey. Thank you for participating.',
        outro_message: createdSurvey.outro_message || 'Thank you for completing the survey!',
        voice_type: createdSurvey.voice_type || 'neutral_female',
        voice_speed: createdSurvey.voice_speed || 'normal',
        max_duration: createdSurvey.max_duration || 10,
        max_retries: createdSurvey.max_retries || 3,
        call_during_business_hours: createdSurvey.call_during_business_hours ?? true,
        avoid_weekends: createdSurvey.avoid_weekends ?? true,
        respect_timezone: createdSurvey.respect_timezone ?? true,
        status: createdSurvey.status || 'draft',
        questions: createdSurvey.questions || []
      });
      
      // Reset dialog state
      setNewSurveyTitle('');
      setNewSurveyDescription('');
      setSelectedTemplate('blank');
      setIsCreateDialogOpen(false);
      
      showToastMessage("New survey created successfully", 'success');
      
      // Refresh surveys list
      await loadSurveys();
      
      // Switch to builder tab
      setActiveTab('builder');
      setIsDirty(false);
      
    } catch (error) {
      showToastMessage(`Failed to create survey: ${error.message}`, 'error');
    } finally {
      setIsCreating(false);
    }
  };
  
  return (
    <div className="mx-auto max-w-5xl p-4">
      {/* Toast notification */}
      {showToast.visible && (
        <div className={`fixed top-4 right-4 p-4 rounded-md shadow-md z-50 max-w-md 
          ${showToast.type === 'error' ? 'bg-red-100 border-l-4 border-red-500' : 
            showToast.type === 'success' ? 'bg-green-100 border-l-4 border-green-500' : 
            'bg-blue-100 border-l-4 border-blue-500'}`}>
          <div className="flex items-start">
            <div className="flex-shrink-0 pt-0.5">
              {showToast.type === 'error' ? <AlertTriangle size={20} className="text-red-500" /> : 
               showToast.type === 'success' ? <Check size={20} className="text-green-500" /> : 
               <div />}
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium">
                {showToast.message}
              </p>
            </div>
            <button 
              className="ml-auto flex-shrink-0 text-gray-400 hover:text-gray-600"
              onClick={() => setShowToast({ visible: false, message: '', type: '' })}
            >
              <X size={16} />
            </button>
          </div>
        </div>
      )}
      
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold">Survey Builder</h1>
          <p className="text-sm text-gray-500 mt-1">
            Build and manage phone feedback surveys
          </p>
        </div>
        <div className="flex space-x-2">
          <Button 
            variant="outline" 
            size="sm"
            className="flex items-center bg-gray-50"
            disabled={!isDirty || isLoading}
            onClick={saveSurvey}
          >
            <Save size={16} className="mr-2" />
            {isSaving ? 'Saving...' : 'Save Changes'}
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button className="flex items-center bg-blue-600" disabled={isLoading}>
                <PlayCircle size={16} className="mr-2" />
                Test Survey
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem onClick={() => setShowTestConfirmation(true)}>
                <Phone size={16} className="mr-2" />
                Test via Phone Call
              </DropdownMenuItem>
              <DropdownMenuItem>
                <LayoutGrid size={16} className="mr-2" />
                Preview in Web Interface
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem>
                <ExternalLink size={16} className="mr-2" />
                Open in Simulator
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
      
      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="all-surveys">All Surveys</TabsTrigger>
          <TabsTrigger value="builder">Survey Builder</TabsTrigger>
          <TabsTrigger value="settings">Survey Settings</TabsTrigger>
        </TabsList>
        
        <TabsContent value="builder">
          {isSurveyLoading || isSwitchingSurvey ? (
            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <Skeleton className="h-6 w-48" />
                  <Skeleton className="h-4 w-32" />
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Skeleton className="h-4 w-16 mb-2" />
                      <Skeleton className="h-10 w-full" />
                    </div>
                    <div>
                      <Skeleton className="h-4 w-20 mb-2" />
                      <Skeleton className="h-10 w-full" />
                    </div>
                  </div>
                </CardContent>
              </Card>
              
              <div className="space-y-4">
                {[1, 2, 3].map(i => <QuestionCardSkeleton key={i} />)}
              </div>
            </div>
          ) : !currentSurvey.id ? (
            <Card className="mb-6">
              <CardContent className="py-12">
                <div className="text-center">
                  <LayoutGrid size={48} className="mx-auto text-gray-400 mb-4" />
                  <h3 className="text-xl font-medium mb-2">No Survey Selected</h3>
                  <p className="text-gray-500 mb-6">
                    Select a survey from the "All Surveys" tab or create a new one to start building.
                  </p>
                  <div className="flex justify-center space-x-4">
                    <Button 
                      onClick={handleBackToSurveys}
                      variant="outline"
                    >
                      <ArrowLeft size={16} className="mr-2" />
                      Back to All Surveys
                    </Button>
                    <Button 
                      onClick={handleCreateNewSurveyFromTab}
                      className="bg-blue-600 hover:bg-blue-700"
                    >
                      <Plus size={16} className="mr-2" />
                      Create New Survey
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ) : (
            <>
              {/* Survey Header */}
              <Card className="mb-6">
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          onClick={handleBackToSurveys}
                          className="px-2"
                        >
                          <ArrowLeft size={16} />
                        </Button>
                        <Input
                          value={currentSurvey.title}
                          onChange={(e) => setCurrentSurvey({ ...currentSurvey, title: e.target.value })}
                          className="text-xl font-semibold bg-transparent border-none px-0 text-gray-900 h-auto"
                          placeholder="Survey Title"
                        />
                      </div>
                      <div className="mt-2">
                        <Textarea
                          value={currentSurvey.description}
                          onChange={(e) => setCurrentSurvey({ ...currentSurvey, description: e.target.value })}
                          className="bg-transparent border-none px-0 text-gray-600 resize-none"
                          placeholder="Survey description (optional)"
                          rows={1}
                        />
                      </div>
                    </div>
                    <div className="ml-4">
                      <Badge 
                        variant={currentSurvey.status === 'active' ? 'default' : 'secondary'}
                        className={currentSurvey.status === 'active' ? 'bg-green-100 text-green-800' : ''}
                      >
                        {currentSurvey.status}
                      </Badge>
                    </div>
                  </div>
                </CardHeader>
              </Card>
              
              {/* Questions */}
              <div className="space-y-6">
                {currentSurvey.questions.map((question, index) => (
                  <QuestionCard 
                    key={question.id} 
                    question={question} 
                    index={index} 
                  />
                ))}
                
                {/* Add Question Button */}
                <Card className="border-2 border-dashed border-gray-300 hover:border-gray-400 transition-colors">
                  <CardContent className="flex items-center justify-center py-8">
                    <Button 
                      variant="ghost" 
                      className="flex items-center text-gray-600 hover:text-gray-900"
                      onClick={addQuestion}
                    >
                      <PlusCircle size={20} className="mr-2" />
                      Add Question
                    </Button>
                  </CardContent>
                </Card>
              </div>
            </>
          )}
        </TabsContent>
        
        <TabsContent value="settings">
          {isSurveyLoading || isSwitchingSurvey ? (
            <SurveySettingsSkeleton />
          ) : !currentSurvey.id ? (
            <Card>
              <CardContent className="py-12">
                <div className="text-center text-gray-500">
                  <Settings size={48} className="mx-auto mb-4 text-gray-400" />
                  <h3 className="text-xl font-medium mb-2">No Survey Selected</h3>
                  <p className="mb-4">Select a survey from the "All Surveys" tab to configure settings.</p>
                  <Button 
                    onClick={() => setActiveTab('all-surveys')}
                    className="bg-blue-600 hover:bg-blue-700"
                  >
                    View All Surveys
                  </Button>
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardHeader>
                <CardTitle>Survey Settings</CardTitle>
                <CardDescription>Configure general settings for this survey</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  <div className="grid grid-cols-2 gap-6">
                    <div className="col-span-2">
                      <Label htmlFor="survey-title" className="mb-1 block">Survey Title</Label>
                      <Input
                        id="survey-title"
                        value={currentSurvey.title}
                        onChange={(e) => setCurrentSurvey({ ...currentSurvey, title: e.target.value })}
                      />
                    </div>
                    
                    <div className="col-span-2">
                      <Label htmlFor="survey-description" className="mb-1 block">Survey Description</Label>
                      <Textarea
                        id="survey-description"
                        value={currentSurvey.description}
                        onChange={(e) => setCurrentSurvey({ ...currentSurvey, description: e.target.value })}
                      />
                    </div>
                  </div>
                  
                  <Separator />
                  
                  <div>
                    <h3 className="text-base font-medium mb-3">Voice Settings</h3>
                    <div className="grid grid-cols-2 gap-6">
                      <div>
                        <Label htmlFor="intro-message" className="mb-1 block">Introduction Message</Label>
                        <Textarea
                          id="intro-message"
                          rows={3}
                          value={currentSurvey.intro_message}
                          onChange={(e) => setCurrentSurvey({ ...currentSurvey, intro_message: e.target.value })}
                        />
                        <p className="text-xs text-gray-500 mt-1">This message is spoken to the caller at the beginning of the survey</p>
                      </div>
                      <div>
                        <Label htmlFor="outro-message" className="mb-1 block">Conclusion Message</Label>
                        <Textarea
                          id="outro-message"
                          rows={3}
                          value={currentSurvey.outro_message}
                          onChange={(e) => setCurrentSurvey({ ...currentSurvey, outro_message: e.target.value })}
                        />
                        <p className="text-xs text-gray-500 mt-1">This message is spoken to the caller at the end of the survey</p>
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-6 mt-4">
                      <div>
                        <Label htmlFor="voice-type" className="mb-1 block">Voice Type</Label>
                        <Select 
                          value={currentSurvey.voice_type}
                          onValueChange={(value) => setCurrentSurvey({ ...currentSurvey, voice_type: value })}
                        >
                          <SelectTrigger id="voice-type">
                            <SelectValue placeholder="Select voice type" />
                          </SelectTrigger>
                          <SelectContent>
                            {voiceTypes.map(type => (
                              <SelectItem key={type.value} value={type.value}>{type.label}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      
                      <div>
                        <Label htmlFor="voice-speed" className="mb-1 block">Voice Speed</Label>
                        <Select 
                          value={currentSurvey.voice_speed}
                          onValueChange={(value) => setCurrentSurvey({ ...currentSurvey, voice_speed: value })}
                        >
                          <SelectTrigger id="voice-speed">
                            <SelectValue placeholder="Select voice speed" />
                          </SelectTrigger>
                          <SelectContent>
                            {speedOptions.map(option => (
                              <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                  </div>
                  
                  <Separator />
                  
                  <div>
                    <h3 className="text-base font-medium mb-3">Call Settings</h3>
                    <div className="grid grid-cols-2 gap-6">
                      <div>
                        <Label htmlFor="max-duration" className="mb-1 block">Maximum Call Duration</Label>
                        <div className="flex">
                          <Input
                            id="max-duration"
                            type="number"
                            min={1}
                            max={30}
                            value={currentSurvey.max_duration}
                            onChange={(e) => setCurrentSurvey({ ...currentSurvey, max_duration: parseInt(e.target.value) })}
                          />
                          <div className="flex items-center ml-2 text-sm text-gray-500">minutes</div>
                        </div>
                      </div>
                      
                      <div>
                        <Label htmlFor="max-retries" className="mb-1 block">Max Retry Attempts</Label>
                        <Input
                          id="max-retries"
                          type="number"
                          min={0}
                          max={5}
                          value={currentSurvey.max_retries}
                          onChange={(e) => setCurrentSurvey({ ...currentSurvey, max_retries: parseInt(e.target.value) })}
                        />
                      </div>
                    </div>
                    
                    <div className="mt-4 space-y-4">
                      <div className="flex items-center space-x-2">
                        <Switch
                          id="business-hours"
                          checked={currentSurvey.call_during_business_hours}
                          onCheckedChange={(checked) => setCurrentSurvey({ ...currentSurvey, call_during_business_hours: checked })}
                        />
                        <Label htmlFor="business-hours">Call only during business hours (9am-5pm)</Label>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        <Switch
                          id="avoid-weekends"
                          checked={currentSurvey.avoid_weekends}
                          onCheckedChange={(checked) => setCurrentSurvey({ ...currentSurvey, avoid_weekends: checked })}
                        />
                        <Label htmlFor="avoid-weekends">Avoid weekends</Label>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        <Switch
                          id="respect-timezone"
                          checked={currentSurvey.respect_timezone}
                          onCheckedChange={(checked) => setCurrentSurvey({ ...currentSurvey, respect_timezone: checked })}
                        />
                        <Label htmlFor="respect-timezone">Respect user's timezone</Label>
                      </div>
                    </div>
                  </div>
                  
                  <Separator />
                  
                  <div>
                    <h3 className="text-base font-medium mb-3">Survey Status</h3>
                    <div className="flex space-x-2">
                      <Button 
                        variant={currentSurvey.status === 'draft' ? 'default' : 'outline'} 
                        size="sm"
                        onClick={() => setCurrentSurvey({ ...currentSurvey, status: 'draft' })}
                      >
                        Draft
                      </Button>
                      <Button 
                        variant={currentSurvey.status === 'active' ? 'default' : 'outline'} 
                        size="sm"
                        onClick={() => setCurrentSurvey({ ...currentSurvey, status: 'active' })}
                      >
                        Active
                      </Button>
                      <Button 
                        variant={currentSurvey.status === 'archived' ? 'default' : 'outline'} 
                        size="sm"
                        onClick={() => setCurrentSurvey({ ...currentSurvey, status: 'archived' })}
                      >
                        Archived
                      </Button>
                    </div>
                  </div>
                </div>
              </CardContent>
              <CardFooter className="flex justify-end border-t pt-6">
                <Button onClick={saveSurvey}>
                  <Save size={16} className="mr-2" />
                  Save Settings
                </Button>
              </CardFooter>
            </Card>
          )}
        </TabsContent>
        
        <TabsContent value="all-surveys">
          <Card>
            <CardHeader>
              <div className="flex justify-between items-center">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    All Surveys
                    {isRefreshing && (
                      <RefreshCw size={16} className="animate-spin text-blue-500" />
                    )}
                  </CardTitle>
                  <CardDescription>Manage your existing surveys or create new ones</CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <Button 
                    variant="outline"
                    size="sm"
                    onClick={() => loadSurveys()}
                    disabled={isLoading || isRefreshing}
                  >
                    <RefreshCw size={16} className={`mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
                    Refresh
                  </Button>
                  <Button 
                    onClick={handleCreateNewSurveyFromTab}
                    className="flex items-center bg-blue-600 hover:bg-blue-700"
                    disabled={isLoading || isCreating}
                  >
                    {isCreating ? (
                      <Loader2 size={16} className="mr-2 animate-spin" />
                    ) : (
                      <Plus size={16} className="mr-2" />
                    )}
                    Create New Survey
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <SurveyListSkeleton />
              ) : (
                <>
                  <div className="border rounded-md overflow-hidden">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Survey Title</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead>Questions</TableHead>
                          <TableHead>Last Modified</TableHead>
                          <TableHead>Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {allSurveys.length === 0 ? (
                          <TableRow>
                            <TableCell colSpan={5} className="text-center py-8">
                              <div className="text-gray-500">
                                <h3 className="text-lg font-medium mb-2">No Surveys Found</h3>
                                <p className="text-sm mb-4">
                                  This means you're a new user or the surveys in the database belong to different users.
                                </p>
                                <Button 
                                  onClick={handleCreateNewSurveyFromTab}
                                  className="bg-blue-600 hover:bg-blue-700"
                                  disabled={isCreating}
                                >
                                  {isCreating ? (
                                    <>
                                      <Loader2 size={16} className="mr-2 animate-spin" />
                                      Creating...
                                    </>
                                  ) : (
                                    'Create Your First Survey'
                                  )}
                                </Button>
                              </div>
                            </TableCell>
                          </TableRow>
                        ) : (
                          allSurveys.map((survey) => (
                            <TableRow 
                              key={survey.id} 
                              className="cursor-pointer hover:bg-gray-50"
                              onClick={() => startEditingSurvey(survey.id)}
                            >
                              <TableCell className="font-medium">{survey.title}</TableCell>
                              <TableCell>
                                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                                  survey.status === 'active' ? 'bg-green-100 text-green-800' :
                                  survey.status === 'draft' ? 'bg-yellow-100 text-yellow-800' :
                                  'bg-gray-100 text-gray-800'
                                }`}>
                                  {survey.status}
                                </span>
                              </TableCell>
                              <TableCell>{survey.questions}</TableCell>
                              <TableCell>{survey.lastModified}</TableCell>
                              <TableCell>
                                <DropdownMenu>
                                  <DropdownMenuTrigger asChild>
                                    <Button 
                                      variant="ghost" 
                                      size="sm"
                                      onClick={(e) => e.stopPropagation()}
                                    >
                                      <MoreHorizontal size={16} />
                                    </Button>
                                  </DropdownMenuTrigger>
                                  <DropdownMenuContent>
                                    <DropdownMenuItem onClick={(e) => {
                                      e.stopPropagation();
                                      startEditingSurvey(survey.id);
                                    }}>
                                      <Pencil size={16} className="mr-2" />
                                      Edit
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onClick={(e) => e.stopPropagation()}>
                                      <Copy size={16} className="mr-2" />
                                      Duplicate
                                    </DropdownMenuItem>
                                    <DropdownMenuSeparator />
                                    <DropdownMenuItem 
                                      className="text-red-600"
                                      onClick={(e) => e.stopPropagation()}
                                    >
                                      <Trash2 size={16} className="mr-2" />
                                      Delete
                                    </DropdownMenuItem>
                                  </DropdownMenuContent>
                                </DropdownMenu>
                              </TableCell>
                            </TableRow>
                          ))
                        )}
                      </TableBody>
                    </Table>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
      
      {/* Logic Dialog */}
      <Dialog open={isLogicDialogOpen} onOpenChange={setIsLogicDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              {selectedQuestionForLogic ? 
                `Define Logic for: ${selectedQuestionForLogic.text.substring(0, 40)}${selectedQuestionForLogic.text.length > 40 ? '...' : ''}` : 
                'Question Logic'}
            </DialogTitle>
          </DialogHeader>
          
          {selectedQuestionForLogic && (
            <div className="py-4">
              <p className="text-sm mb-4">
                Define what question to show next based on the answer to this question.
              </p>
              
              {getLogicConditions(selectedQuestionForLogic.question_type, selectedQuestionForLogic.options).map(condition => {
                const targetId = selectedQuestionForLogic.follow_up_logic[condition.value];
                
                return (
                  <div key={condition.value} className="mb-4 p-3 border rounded-md bg-gray-50">
                    <Label className="font-medium text-sm">{condition.label}</Label>
                    <div className="mt-2">
                      <Select 
                        value={targetId || ''}
                        onValueChange={(value) => handleUpdateLogic(condition.value, value)}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select next question" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="">No specific follow-up (continue to next)</SelectItem>
                          {currentSurvey.questions
                            .filter(q => q.id !== selectedQuestionForLogic.id)
                            .map((q, idx) => (
                              <SelectItem key={q.id} value={q.id}>
                                Q{currentSurvey.questions.indexOf(q) + 1}: {q.text.substring(0, 30)}{q.text.length > 30 ? '...' : ''}
                              </SelectItem>
                            ))
                          }
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsLogicDialogOpen(false)}>
              Close
            </Button>
            <Button onClick={() => setIsLogicDialogOpen(false)}>
              Save Logic
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Test Survey Dialog */}
      <Dialog open={showTestConfirmation} onOpenChange={setShowTestConfirmation}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Test Survey</DialogTitle>
          </DialogHeader>
          
          <div className="py-4">
            <p className="mb-4">Enter a phone number to test this survey:</p>
            
            <div className="mb-4">
              <Label htmlFor="test-phone" className="mb-1 block">Phone Number</Label>
              <Input
                id="test-phone"
                placeholder="+1 (555) 000-0000"
              />
            </div>
            
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-md flex">
              <div className="text-blue-500 mr-2 mt-0.5">
                <AlertTriangle size={18} />
              </div>
              <div className="text-sm text-blue-700">
                This will place a real test call using the current version of the survey.
              </div>
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowTestConfirmation(false)}>
              Cancel
            </Button>
            <Button 
              onClick={() => {
                setShowTestConfirmation(false);
                showToastMessage("Test call initiated! You'll receive a call shortly.", 'success');
              }}
            >
              Start Test Call
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* ***** Create New Survey Dialog ***** */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Create New Survey</DialogTitle>
          </DialogHeader>
          
          <div className="py-4">
            <div className="space-y-4">
              <div>
                <Label htmlFor="new-survey-title" className="mb-1 block">Survey Title</Label>
                <Input
                  id="new-survey-title"
                  placeholder="Enter survey title"
                  value={newSurveyTitle}
                  onChange={(e) => setNewSurveyTitle(e.target.value)}
                />
              </div>
              
              <div>
                <Label htmlFor="new-survey-description" className="mb-1 block">Survey Description (optional)</Label>
                <Textarea
                  id="new-survey-description"
                  placeholder="Enter a brief description"
                  value={newSurveyDescription}
                  onChange={(e) => setNewSurveyDescription(e.target.value)}
                />
              </div>
              
              <div>
                <Label className="mb-2 block">Start with a Template</Label>
                <div className="grid grid-cols-3 gap-3">
                  <div 
                    className={`border rounded-md p-3 flex flex-col items-center hover:bg-blue-50 cursor-pointer transition-colors ${selectedTemplate === 'blank' ? 'border-blue-500 bg-blue-50' : ''}`}
                    onClick={() => setSelectedTemplate('blank')}
                  >
                    <div className="h-10 w-10 flex items-center justify-center bg-gray-100 rounded-full mb-2">
                      <PlusCircle size={20} className="text-gray-600" />
                    </div>
                    <span className="text-sm font-medium">Blank</span>
                    <span className="text-xs text-gray-500">Start from scratch</span>
                  </div>
                  
                  <div 
                    className={`border rounded-md p-3 flex flex-col items-center hover:bg-blue-50 cursor-pointer transition-colors ${selectedTemplate === 'satisfaction' ? 'border-blue-500 bg-blue-50' : ''}`}
                    onClick={() => setSelectedTemplate('satisfaction')}
                  >
                    <div className="h-10 w-10 flex items-center justify-center bg-green-100 rounded-full mb-2">
                      <Check size={20} className="text-green-600" />
                    </div>
                    <span className="text-sm font-medium">Satisfaction</span>
                    <span className="text-xs text-gray-500">3 questions</span>
                  </div>
                  
                  <div 
                    className={`border rounded-md p-3 flex flex-col items-center hover:bg-blue-50 cursor-pointer transition-colors ${selectedTemplate === 'feedback' ? 'border-blue-500 bg-blue-50' : ''}`}
                    onClick={() => setSelectedTemplate('feedback')}
                  >
                    <div className="h-10 w-10 flex items-center justify-center bg-blue-100 rounded-full mb-2">
                      <MessageSquare size={20} className="text-blue-600" />
                    </div>
                    <span className="text-sm font-medium">Feedback</span>
                    <span className="text-xs text-gray-500">3 questions</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => {
                setIsCreateDialogOpen(false);
                setNewSurveyTitle('');
                setNewSurveyDescription('');
                setSelectedTemplate('blank');
              }}
              disabled={isCreating}
            >
              Cancel
            </Button>
            <Button 
              onClick={handleCreateNewSurvey}
              className="bg-blue-600 hover:bg-blue-700"
              disabled={isCreating || !newSurveyTitle.trim()}
            >
              {isCreating ? 'Creating...' : 'Create Survey'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default SurveyBuilder;
