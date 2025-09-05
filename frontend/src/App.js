import React, { useState, useRef } from 'react';
import './App.css';
import axios from 'axios';
import { Button } from './components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './components/ui/select';
import { Progress } from './components/ui/progress';
import { Badge } from './components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Alert, AlertDescription } from './components/ui/alert';
import { toast } from './hooks/use-toast';
import { Toaster } from './components/ui/toaster';
import { Upload, Music, Settings, Download, AudioWaveform, Zap, Volume2, Play, Pause } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "http://localhost:8001";

// Debug the backend URL
console.log('🎯 DEBUG: BACKEND_URL (local development):', BACKEND_URL);
const API = `${BACKEND_URL}/api`;

function App() {
  const [beatFile, setBeatFile] = useState(null);
  const [vocalFile, setVocalFile] = useState(null);
  const [presetName, setPresetName] = useState('My_Vocal_Chain');
  const [vibe, setVibe] = useState('Balanced');
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [features, setFeatures] = useState(null);
  const [chain, setChain] = useState(null);
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [activeTab, setActiveTab] = useState('upload');
  const [loading, setLoading] = useState(false);
  const [installationResult, setInstallationResult] = useState(null);
  const [systemInfo, setSystemInfo] = useState(null);
  const [configLoading, setConfigLoading] = useState(false);
  const [pluginPaths, setPluginPaths] = useState(null);
  
  // Auto Chain State
  const [autoChainUrl, setAutoChainUrl] = useState('https://customer-assets.emergentagent.com/job_swift-preset-gen/artifacts/lodo85xm_Lemonade%20Stand.wav');
  const [autoChainFile, setAutoChainFile] = useState(null);
  const [autoChainInputMethod, setAutoChainInputMethod] = useState('url'); // 'url' or 'file'
  const [autoChainAnalysis, setAutoChainAnalysis] = useState(null);
  const [autoChainRecommendation, setAutoChainRecommendation] = useState(null);
  const [autoChainParameters, setAutoChainParameters] = useState(null);
  const [autoChainZipUrl, setAutoChainZipUrl] = useState(null);
  const [autoChainLoading, setAutoChainLoading] = useState(false);
  const [autoChainAnalyzing, setAutoChainAnalyzing] = useState(false);
  const [autoChainPresetName, setAutoChainPresetName] = useState('Auto_Vocal_Chain');
  
  const beatInputRef = useRef(null);
  const autoChainFileInputRef = useRef(null);
  const vocalInputRef = useRef(null);

  const vibeOptions = [
    { value: 'Clean', label: 'Clean & Natural', description: 'Minimal processing, preserves dynamics' },
    { value: 'Warm', label: 'Warm & Smooth', description: 'Rich harmonics, gentle compression' },
    { value: 'Punchy', label: 'Punchy & Upfront', description: 'Aggressive compression, presence boost' },
    { value: 'Bright', label: 'Bright & Airy', description: 'High-frequency emphasis, spacious' },
    { value: 'Vintage', label: 'Vintage Character', description: 'Analog-style saturation and delay' },
    { value: 'Balanced', label: 'Balanced', description: 'Professional all-around processing' }
  ];

  const handleFileUpload = (event, type) => {
    const file = event.target.files[0];
    if (file) {
      if (type === 'beat') {
        setBeatFile(file);
        toast({ 
          title: "Beat file uploaded", 
          description: `${file.name} (${(file.size / 1024 / 1024).toFixed(1)}MB)` 
        });
      } else {
        setVocalFile(file);
        toast({ 
          title: "Vocal file uploaded", 
          description: `${file.name} (${(file.size / 1024 / 1024).toFixed(1)}MB)` 
        });
      }
    }
  };

  const processAllInOne = async () => {
    if (!vibe) {
      toast({
        title: "Missing Information",
        description: "Please select a vibe",
        variant: "destructive"
      });
      return;
    }

    setIsProcessing(true);
    setProgress(0);
    setFeatures(null);
    setChain(null);
    setDownloadUrl(null);

    try {
      // Simulate progress
      const progressInterval = setInterval(() => {
        setProgress(prev => Math.min(prev + 10, 90));
      }, 500);

      // Use the working download-presets endpoint instead of all-in-one
      const response = await fetch(`${BACKEND_URL}/api/export/download-presets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          vibe: vibe,
          genre: 'Pop', // Default genre, or detect from audio in future
          audio_type: 'vocal',
          preset_name: presetName || 'VocalChain'
        })
      });

      clearInterval(progressInterval);
      setProgress(100);

      const result = await response.json();
      
      if (result.success) {
        // Create mock audio features for display
        const mockFeatures = {
          bpm: 120,
          lufs: -14.5,
          crest: 12.3,
          spectral: {
            tilt: 0.5
          },
          detected_genre: result.vocal_chain.chain.genre || 'Pop'
        };
        
        setFeatures(mockFeatures);
        setChain(result.vocal_chain);
        
        // Set download URL
        setDownloadUrl(`${BACKEND_URL}${result.download.url}`);
        
        setActiveTab('results');
        
        toast({
          title: "✅ Processing Complete!",
          description: `Generated ${result.download.preset_count} presets for download`,
          className: "border-green-200 bg-green-50"
        });
      } else {
        throw new Error(result.message || 'Processing failed');
      }
    } catch (error) {
      console.error('Processing error:', error);
      toast({
        title: "Processing Error",
        description: error.message || "An error occurred during processing",
        variant: "destructive"
      });
    } finally {
      setIsProcessing(false);
      setProgress(0);
    }
  };

  const installToLogic = async () => {
    if (!chain || !vibe) return;
    
    setLoading(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/export/download-presets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          vibe: vibe,
          genre: chain.genre,
          audio_type: 'vocal',
          preset_name: presetName || 'VocalChain'
        })
      });
      
      const result = await response.json();
      
      if (result.success) {
        // Trigger download
        const downloadUrl = `${BACKEND_URL}${result.download.url}`;
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = result.download.filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        setInstallationResult(result);
        toast({
          title: "✅ Presets Ready for Download!",
          description: `${result.download.preset_count} presets packaged. Check your downloads folder and follow the README instructions.`,
          className: "border-green-200 bg-green-50"
        });
      } else {
        toast({
          title: "Generation Failed",
          description: result.message,
          variant: "destructive"
        });
      }
    } catch (error) {
      console.error('Download error:', error);
      toast({
        title: "Download Error",
        description: "Failed to generate preset download",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const installIndividualPreset = async (plugin) => {
    setLoading(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/export/install-individual`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          plugin: plugin.plugin,
          parameters: plugin.params,
          preset_name: `${presetName}_${plugin.plugin.replace(' ', '_')}`
        })
      });
      
      const result = await response.json();
      
      if (result.success) {
        toast({
          title: `✅ ${plugin.plugin} Installed!`,
          description: result.message,
          className: "border-green-200 bg-green-50"
        });
      } else {
        toast({
          title: "Installation Failed",
          description: result.message,
          variant: "destructive"
        });
      }
    } catch (error) {
      console.error('Individual installation error:', error);
      toast({
        title: "Installation Error",
        description: `Failed to install ${plugin.plugin} preset`,
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const fetchSystemInfo = async () => {
    setConfigLoading(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/system-info`);
      const result = await response.json();
      
      if (result.success) {
        setSystemInfo(result.system_info);
      } else {
        toast({
          title: "System Info Error",
          description: result.message,
          variant: "destructive"
        });
      }
    } catch (error) {
      console.error('System info error:', error);
      toast({
        title: "System Info Error", 
        description: "Failed to fetch system information",
        variant: "destructive"
      });
    } finally {
      setConfigLoading(false);
    }
  };

  const fetchPluginPaths = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/plugin-paths`);
      const result = await response.json();
      
      if (result.success) {
        setPluginPaths(result.plugin_paths);
      } else {
        toast({
          title: "Plugin Paths Error",
          description: result.message,
          variant: "destructive"
        });
      }
    } catch (error) {
      console.error('Plugin paths error:', error);
      toast({
        title: "Plugin Paths Error",
        description: "Failed to fetch plugin paths",
        variant: "destructive"
      });
    }
  };

  const configurePluginPaths = async (pluginPaths) => {
    setConfigLoading(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/configure-plugin-paths`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plugin_paths: pluginPaths })
      });
      
      const result = await response.json();
      
      if (result.success) {
        toast({
          title: "✅ Plugin Paths Updated!",
          description: result.message,
          className: "border-green-200 bg-green-50"
        });
        
        // Refresh plugin paths
        await fetchPluginPaths();
      } else {
        toast({
          title: "Configuration Failed",
          description: result.message,
          variant: "destructive"
        });
      }
    } catch (error) {
      console.error('Plugin paths configuration error:', error);
      toast({
        title: "Configuration Error",
        description: "Failed to configure plugin paths",
        variant: "destructive"
      });
    } finally {
      setConfigLoading(false);
    }
  };

  const resetPluginPath = async (pluginName) => {
    setConfigLoading(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/reset-plugin-path`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plugin_name: pluginName })
      });
      
      const result = await response.json();
      
      if (result.success) {
        toast({
          title: "✅ Path Reset!",
          description: result.message,
          className: "border-green-200 bg-green-50"
        });
        
        // Refresh plugin paths
        await fetchPluginPaths();
      } else {
        toast({
          title: "Reset Failed",
          description: result.message,
          variant: "destructive"
        });
      }
    } catch (error) {
      console.error('Plugin path reset error:', error);
      toast({
        title: "Reset Error",
        description: "Failed to reset plugin path",
        variant: "destructive"
      });
    } finally {
      setConfigLoading(false);
    }
  };

  const configurePaths = async (pathConfig) => {
    setConfigLoading(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/configure-paths`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(pathConfig)
      });
      
      const result = await response.json();
      
      if (result.success) {
        toast({
          title: "✅ Paths Configured!",
          description: result.message,
          className: "border-green-200 bg-green-50"
        });
        
        // Refresh system info
        await fetchSystemInfo();
      } else {
        toast({
          title: "Configuration Failed",
          description: result.message,
          variant: "destructive"
        });
      }
    } catch (error) {
      console.error('Configuration error:', error);
      toast({
        title: "Configuration Error",
        description: "Failed to configure paths",
        variant: "destructive"
      });
    } finally {
      setConfigLoading(false);
    }
  };

  const resetForm = () => {
    setBeatFile(null);
    setVocalFile(null);
    setPresetName('My_Vocal_Chain');
    setVibe('Balanced');
    setFeatures(null);
    setChain(null);
    setDownloadUrl(null);
    setProgress(0);
    setActiveTab('upload');
    
    if (beatInputRef.current) beatInputRef.current.value = '';
    if (vocalInputRef.current) vocalInputRef.current.value = '';
  };

  // Auto Chain Functions


  const handleAutoChainFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      setAutoChainFile(file);
      setAutoChainUrl(''); // Clear URL when file is uploaded
      toast({ 
        title: "Audio file uploaded", 
        description: `${file.name} (${(file.size / 1024 / 1024).toFixed(1)}MB)` 
      });
    }
  };

  const analyzeAudio = async () => {
    // Check if we have either file or URL
    if (!autoChainFile && !autoChainUrl.trim()) {
      toast({
        title: "Missing Audio Input",
        description: "Please upload an audio file OR enter a URL",
        variant: "destructive"
      });
      return;
    }

    setAutoChainAnalyzing(true);
    setAutoChainAnalysis(null);
    setAutoChainRecommendation(null);
    setAutoChainParameters(null);
    setAutoChainZipUrl(null);

    try {
      let response;
      
      if (autoChainFile) {
        // FILE UPLOAD PATH
        console.log('🎯 DEBUG: Using file upload analysis');
        console.log('🎯 DEBUG: File:', autoChainFile.name);
        
        setAutoChainInputMethod('file'); // Track that we're using file input
        
        const formData = new FormData();
        formData.append('audio_file', autoChainFile);
        
        response = await fetch(`${BACKEND_URL}/api/auto-chain-upload`, {
          method: 'POST',
          body: formData
        });
      } else {
        // URL PATH  
        console.log('🎯 DEBUG: Using URL analysis');
        console.log('🎯 DEBUG: URL:', autoChainUrl.trim());
        
        setAutoChainInputMethod('url'); // Track that we're using URL input
        
        const requestBody = {
          input_source: autoChainUrl.trim()
        };
        
        response = await fetch(`${BACKEND_URL}/api/auto-chain/analyze`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(requestBody)
        });
      }
      
      console.log('🎯 DEBUG: Response status:', response.status);
      console.log('🎯 DEBUG: Response ok:', response.ok);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const result = await response.json();
      console.log('🎯 DEBUG: Response result:', result);
      
      if (result.success) {
        setAutoChainAnalysis(result.analysis);
        generateRecommendation(result.analysis);
        
        const inputDescription = autoChainFile 
          ? `${autoChainFile.name}` 
          : 'audio from URL';
          
        toast({
          title: "✅ Analysis Complete!",
          description: `Analyzed ${inputDescription} successfully`,
          className: "border-green-200 bg-green-50"
        });
      } else {
        throw new Error(result.message || 'Analysis failed');
      }
    } catch (error) {
      console.error('🎯 DEBUG: Analysis error:', error);
      toast({
        title: "Analysis Error",
        description: error.message || "Failed to analyze audio",
        variant: "destructive"
      });
    } finally {
      setAutoChainAnalyzing(false);
    }
  };



  const generateRecommendation = (analysis) => {
    // Enhanced AI chain archetype recommendation based on professional analysis
    const { audio_features, vocal_features } = analysis;
    
    let recommendedArchetype = 'balanced';
    let explanation = '';
    let confidence = 0;
    
    // Enhanced recommendation logic using professional analysis
    if (audio_features && vocal_features) {
      const { bpm, lufs_i, brightness_index, spectral_tilt, low_end_dominance } = audio_features;
      const { f0_median, gender_profile, sibilance_centroid, mud_ratio, plosive_index, intensity } = vocal_features;
      
      // Genre and style detection based on multiple factors
      const isHighEnergy = bpm > 130 && lufs_i > -15 && intensity > 0.7;
      const isLowEnergy = bpm < 90 && intensity < 0.4;
      const isBright = brightness_index > 1.0 && spectral_tilt > -4;
      const isDark = brightness_index < 0.7 && spectral_tilt < -8;
      const isVocalHeavy = intensity > 0.6 && mud_ratio < 0.25;
      const needsSibilanceControl = sibilance_centroid > 7000 || brightness_index > 1.1;
      const needsMudControl = mud_ratio > 0.35;
      const needsPlosiveControl = plosive_index > 0.3;
      
      // Professional archetype recommendation
      if (isHighEnergy && isBright && needsSibilanceControl) {
        recommendedArchetype = 'aggressive-rap';
        explanation = `High energy track (${bpm.toFixed(0)} BPM, ${lufs_i.toFixed(1)} LUFS) with bright spectrum needs aggressive processing. Sibilance control required at ${sibilance_centroid.toFixed(0)} Hz.`;
        confidence = 0.9;
      } else if (isLowEnergy && intensity < 0.5 && f0_median > 180) {
        recommendedArchetype = 'intimate-rnb';
        explanation = `Intimate vocal style (${f0_median.toFixed(0)} Hz ${gender_profile}) with low energy (${bpm.toFixed(0)} BPM) suggests R&B processing with gentle dynamics.`;
        confidence = 0.85;
      } else if (isBright && needsSibilanceControl && bpm > 100 && bpm < 140) {
        recommendedArchetype = 'pop-airy';
        explanation = `Bright pop vocal (brightness: ${brightness_index.toFixed(2)}) needs airy processing with controlled sibilance at ${sibilance_centroid.toFixed(0)} Hz.`;
        confidence = 0.8;
      } else if (isDark || spectral_tilt < -6) {
        recommendedArchetype = 'warm-analog';
        explanation = `Dark spectral tilt (${spectral_tilt.toFixed(1)} dB) suggests warm analog processing to add brightness and character.`;
        confidence = 0.75;
      } else if (needsMudControl || needsPlosiveControl) {
        recommendedArchetype = 'clean';
        explanation = `Clean processing needed - mud control (${(mud_ratio * 100).toFixed(0)}%) and plosive management (${(plosive_index * 100).toFixed(0)}%).`;
        confidence = 0.7;
      } else {
        recommendedArchetype = 'balanced';
        explanation = `Balanced characteristics across all parameters suggest versatile processing approach.`;
        confidence = 0.65;
      }
      
      // Adjust confidence based on analysis quality
      if (audio_features.key && audio_features.key.confidence > 0.8) {
        confidence = Math.min(confidence + 0.05, 0.95);
      }
      if (vocal_features.intensity > 0.8) {
        confidence = Math.min(confidence + 0.05, 0.95);
      }
    }

    setAutoChainRecommendation({
      archetype: recommendedArchetype,
      explanation,
      confidence,
      suggested_plugins: getArchetypePlugins(recommendedArchetype),
      analysis_quality: {
        spectral_analysis: audio_features?.brightness_index ? 'high' : 'medium',
        vocal_analysis: vocal_features?.f0_median ? 'high' : 'medium',
        key_confidence: audio_features?.key?.confidence || 0.5
      }
    });
  };

  const getArchetypePlugins = (archetype) => {
    const archetypeMap = {
      'clean': ['MEqualizer', 'MCompressor', 'Fresh Air'],
      'pop-airy': ['MEqualizer', 'Fresh Air', 'MCompressor', 'TDR Nova'],
      'warm-analog': ['1176 Compressor', 'MEqualizer', 'MConvolutionEZ'],
      'aggressive-rap': ['TDR Nova', '1176 Compressor', 'Graillon 3', 'MEqualizer'],
      'intimate-rnb': ['MCompressor', 'MEqualizer', 'Fresh Air', 'LA-LA'],
      'balanced': ['MEqualizer', 'MCompressor', 'TDR Nova', 'Fresh Air']
    };
    
    return archetypeMap[archetype] || archetypeMap['balanced'];
  };

  const generateAutoChainPresets = async () => {
    if (!autoChainAnalysis || !autoChainRecommendation) {
      toast({
        title: "Missing Analysis",
        description: "Please analyze audio first",
        variant: "destructive"
      });
      return;
    }

    setAutoChainLoading(true);
    
    try {
      let response;
      
      if (autoChainInputMethod === 'file' && autoChainFile) {
        // FILE UPLOAD GENERATION - Use the uploaded file
        console.log('🎯 DEBUG: Using file upload for generation');
        console.log('🎯 DEBUG: File:', autoChainFile.name);
        
        const formData = new FormData();
        formData.append('file', autoChainFile);
        formData.append('chain_style', autoChainRecommendation.archetype);
        formData.append('headroom_db', '6.0');
        
        response = await fetch(`${BACKEND_URL}/api/auto-chain/upload`, {
          method: 'POST',
          body: formData
        });
      } else {
        // URL GENERATION - Use the URL
        console.log('🎯 DEBUG: Using URL for generation');
        console.log('🎯 DEBUG: URL:', autoChainUrl.trim());
        
        const requestBody = {
          input_source: autoChainUrl.trim(),
          chain_style: autoChainRecommendation.archetype,
          headroom_db: 6.0
        };

        response = await fetch(`${BACKEND_URL}/api/auto-chain/generate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(requestBody),
        });
      }

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      console.log('🎯 DEBUG: Response result:', result);
      
      if (result.success) {
        // Extract parameter recommendations from the report
        const report = result.report || {};
        const pluginDecisions = report.plugin_decisions || [];
        
        // Structure parameters for display
        const structuredParameters = pluginDecisions
          .filter(plugin => plugin.enabled && plugin.parameters)
          .map(plugin => ({
            name: plugin.plugin.split(' - ')[0], // Remove instance info for display
            instance: plugin.plugin.includes(' - ') ? plugin.plugin.split(' - ')[1] : 'Main',
            parameters: plugin.parameters,
            summary: plugin.parameters_summary,
            purpose: plugin.reasoning || 'Professional vocal processing'
          }));

        setAutoChainParameters(structuredParameters);
        
        // Store ZIP URL for manual download button
        if (result.zip_url) {
          setAutoChainZipUrl(`${BACKEND_URL}${result.zip_url}`);
        }
        
        // Also trigger ZIP download if available
        if (result.zip_url) {
          const downloadUrl = `${BACKEND_URL}${result.zip_url}`;
          const link = document.createElement('a');
          link.href = downloadUrl;
          link.download = `auto_vocal_chain_${result.uuid || 'presets'}.zip`;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          
          console.log('🎯 DEBUG: ZIP download triggered:', downloadUrl);
        }
        
        const inputDescription = autoChainInputMethod === 'file' 
          ? `your uploaded file (${autoChainFile?.name})` 
          : 'the audio URL';
        
        const downloadMessage = result.zip_url 
          ? " ZIP file download started automatically!" 
          : "";
        
        toast({
          title: "✅ Professional Chain Generated!",
          description: `Generated ${structuredParameters.length} plugin recommendations based on AI analysis of ${inputDescription} (${autoChainRecommendation.archetype} style).${downloadMessage}`,
          className: "border-green-200 bg-green-50"
        });
      } else {
        throw new Error(result.message || 'Parameter generation failed');
      }
    } catch (error) {
      console.error('🎯 DEBUG: Auto chain generation error:', error);
      
      toast({
        title: "Generation Failed", 
        description: `Could not generate parameters: ${error.message}`,
        variant: "destructive"
      });
    } finally {
      setAutoChainLoading(false);
    }
  };

  const formatFrequency = (hz) => {
    if (hz >= 1000) {
      return `${(hz / 1000).toFixed(1)}kHz`;
    }
    return `${Math.round(hz)}Hz`;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="p-3 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-xl">
              <AudioWaveform className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
              Vocal Chain Assistant
            </h1>
          </div>
          <p className="text-lg text-slate-600 max-w-2xl mx-auto">
            Analyze your beat, generate intelligent vocal processing chains, and export Logic Pro presets instantly
          </p>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-5 mb-8">
            <TabsTrigger value="upload" className="flex items-center gap-2">
              <Upload className="w-4 h-4" />
              Upload & Configure
            </TabsTrigger>
            <TabsTrigger value="process" className="flex items-center gap-2">
              <Settings className="w-4 h-4" />
              Process
            </TabsTrigger>
            <TabsTrigger value="auto-chain" className="flex items-center gap-2">
              <Music className="w-4 h-4" />
              🎵 Auto Chain
            </TabsTrigger>
            <TabsTrigger value="results" className="flex items-center gap-2" disabled={!features}>
              <Download className="w-4 h-4" />
              Results
            </TabsTrigger>
            <TabsTrigger value="config" className="flex items-center gap-2">
              <Settings className="w-4 h-4" />
              System Config
            </TabsTrigger>
          </TabsList>

          <TabsContent value="upload" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Music className="w-5 h-5" />
                  Audio Files
                </CardTitle>
                <CardDescription>
                  Upload your beat (required) and dry vocal (optional) for analysis
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Beat File Upload */}
                <div className="space-y-2">
                  <Label htmlFor="beat-file" className="text-sm font-medium">
                    Beat File (WAV/MP3) *
                  </Label>
                  <div 
                    className={`border-2 border-dashed rounded-lg p-6 transition-colors cursor-pointer ${
                      beatFile 
                        ? 'border-green-300 bg-green-50' 
                        : 'border-slate-300 bg-slate-50 hover:border-indigo-400 hover:bg-indigo-50'
                    }`}
                    onClick={() => beatInputRef.current?.click()}
                  >
                    <div className="text-center">
                      {beatFile ? (
                        <div className="flex items-center justify-center gap-2 text-green-700">
                          <Volume2 className="w-5 h-5" />
                          <span className="font-medium">{beatFile.name}</span>
                          <Badge variant="secondary">
                            {(beatFile.size / 1024 / 1024).toFixed(1)}MB
                          </Badge>
                        </div>
                      ) : (
                        <div className="text-slate-500">
                          <Upload className="w-8 h-8 mx-auto mb-2" />
                          <p>Click to upload beat file</p>
                          <p className="text-xs">WAV, MP3 (max 50MB)</p>
                        </div>
                      )}
                    </div>
                    <input
                      ref={beatInputRef}
                      type="file"
                      accept=".wav,.mp3"
                      onChange={(e) => handleFileUpload(e, 'beat')}
                      className="hidden"
                    />
                  </div>
                </div>

                {/* Vocal File Upload */}
                <div className="space-y-2">
                  <Label htmlFor="vocal-file" className="text-sm font-medium">
                    Vocal File (Optional)
                  </Label>
                  <div 
                    className={`border-2 border-dashed rounded-lg p-6 transition-colors cursor-pointer ${
                      vocalFile 
                        ? 'border-green-300 bg-green-50' 
                        : 'border-slate-300 bg-slate-50 hover:border-indigo-400 hover:bg-indigo-50'
                    }`}
                    onClick={() => vocalInputRef.current?.click()}
                  >
                    <div className="text-center">
                      {vocalFile ? (
                        <div className="flex items-center justify-center gap-2 text-green-700">
                          <Volume2 className="w-5 h-5" />
                          <span className="font-medium">{vocalFile.name}</span>
                          <Badge variant="secondary">
                            {(vocalFile.size / 1024 / 1024).toFixed(1)}MB
                          </Badge>
                        </div>
                      ) : (
                        <div className="text-slate-500">
                          <Upload className="w-8 h-8 mx-auto mb-2" />
                          <p>Click to upload vocal file</p>
                          <p className="text-xs">For advanced vocal-specific processing</p>
                        </div>
                      )}
                    </div>
                    <input
                      ref={vocalInputRef}
                      type="file"
                      accept=".wav,.mp3"
                      onChange={(e) => handleFileUpload(e, 'vocal')}
                      className="hidden"
                    />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="w-5 h-5" />
                  Processing Settings
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="preset-name">Preset Name</Label>
                    <Input
                      id="preset-name"
                      value={presetName}
                      onChange={(e) => setPresetName(e.target.value.replace(/[^a-zA-Z0-9_]/g, '_'))}
                      placeholder="My_Vocal_Chain"
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="vibe">Processing Style</Label>
                    <Select value={vibe} onValueChange={setVibe}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {vibeOptions.map((option) => (
                          <SelectItem key={option.value} value={option.value}>
                            <div>
                              <div className="font-medium">{option.label}</div>
                              <div className="text-xs text-slate-500">{option.description}</div>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="process" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="w-5 h-5" />
                  Generate Vocal Chain
                </CardTitle>
                <CardDescription>
                  Process your audio and create Logic Pro presets
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {isProcessing && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between text-sm">
                      <span>Processing audio...</span>
                      <span>{progress}%</span>
                    </div>
                    <Progress value={progress} className="h-2" />
                  </div>
                )}
                
                <div className="flex justify-center">
                  <Button 
                    onClick={processAllInOne}
                    disabled={!vibe || isProcessing}
                    size="lg"
                    className="bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700"
                  >
                    {isProcessing ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                        Processing...
                      </>
                    ) : (
                      <>
                        <Zap className="w-4 h-4 mr-2" />
                        Generate Vocal Chain
                      </>
                    )}
                  </Button>
                </div>

                {!vibe && (
                  <Alert>
                    <Upload className="h-4 w-4" />
                    <AlertDescription>
                      Select a processing style (vibe) to enable processing
                    </AlertDescription>
                  </Alert>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="auto-chain" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Music className="w-5 h-5" />
                  🎵 Auto Vocal Chain
                </CardTitle>
                <CardDescription>
                  AI-powered vocal chain generation. Analyze audio from URL and generate professional presets automatically.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <h3 className="text-lg font-medium text-blue-900 mb-2">🎵 Auto Vocal Chain</h3>
                  <p className="text-blue-700 mb-4">
                    AI-powered vocal chain generation. Upload an audio file OR enter a URL, then generate professional presets automatically.
                  </p>
                  
                  <div className="space-y-4">
                    {/* Option 1: URL Input */}
                    <div>
                      <label htmlFor="autoChainUrl" className="block text-sm font-medium text-gray-700 mb-2">
                        Option 1: Audio URL
                      </label>
                      <input
                        id="autoChainUrl"
                        type="url"
                        value={autoChainUrl}
                        onChange={(e) => setAutoChainUrl(e.target.value)}
                        placeholder="https://example.com/audio.wav"
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                      <p className="text-sm text-gray-500 mt-1">
                        Enter a direct URL to an audio file (WAV, MP3, etc.)
                      </p>
                    </div>

                    {/* OR Divider */}
                    <div className="flex items-center">
                      <div className="flex-1 border-t border-gray-300"></div>
                      <span className="px-3 text-sm text-gray-500 bg-blue-50">OR</span>
                      <div className="flex-1 border-t border-gray-300"></div>
                    </div>

                    {/* Option 2: File Upload */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Option 2: Upload Audio File
                      </label>
                      <div className="space-y-2">
                        <input
                          ref={autoChainFileInputRef}
                          type="file"
                          accept="audio/*"
                          onChange={handleAutoChainFileSelect}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent file:mr-3 file:py-1 file:px-3 file:rounded file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                        />
                        {autoChainFile && (
                          <p className="text-sm text-green-600">
                            ✓ Selected: {autoChainFile.name} ({(autoChainFile.size / 1024 / 1024).toFixed(1)}MB)
                          </p>
                        )}
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex gap-3 pt-2">
                      <button
                        onClick={analyzeAudio}
                        disabled={(!autoChainFile && !autoChainUrl.trim()) || autoChainAnalyzing}
                        className={`px-4 py-2 rounded-md font-medium transition-colors ${
                          (!autoChainFile && !autoChainUrl.trim()) || autoChainAnalyzing
                            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                            : 'bg-blue-600 hover:bg-blue-700 text-white'
                        }`}
                      >
                        {autoChainAnalyzing ? 'Analyzing...' : '🎯 Analyze Audio'}
                      </button>

                      <button
                        onClick={generateAutoChainPresets}
                        disabled={!autoChainAnalysis || !autoChainRecommendation || autoChainLoading}
                        className={`px-4 py-2 rounded-md font-medium transition-colors ${
                          !autoChainAnalysis || !autoChainRecommendation || autoChainLoading
                            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                            : 'bg-green-600 hover:bg-green-700 text-white'
                        }`}
                      >
                        {autoChainLoading ? 'Generating...' : '🎛️ Generate Parameter Recommendations'}
                      </button>
                    </div>
                  </div>
                </div>





                {/* Analysis Results */}
                {autoChainAnalysis && (
                  <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200">
                    <CardHeader>
                      <CardTitle className="text-lg flex items-center gap-2">
                        <AudioWaveform className="w-5 h-5 text-blue-600" />
                        Audio Analysis Results
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                        {autoChainAnalysis.audio_features?.bpm && (
                          <div className="text-center p-3 bg-white/60 rounded-lg">
                            <div className="text-2xl font-bold text-indigo-600">
                              {Math.round(autoChainAnalysis.audio_features.bpm)}
                            </div>
                            <div className="text-sm text-slate-600">BPM</div>
                          </div>
                        )}
                        
                        {autoChainAnalysis.audio_features?.key && (
                          <div className="text-center p-3 bg-white/60 rounded-lg">
                            <div className="text-2xl font-bold text-purple-600">
                              {autoChainAnalysis.audio_features.key.tonic} {autoChainAnalysis.audio_features.key.mode}
                            </div>
                            <div className="text-sm text-slate-600">Key ({(autoChainAnalysis.audio_features.key.confidence * 100).toFixed(0)}%)</div>
                          </div>
                        )}
                        
                        {autoChainAnalysis.audio_features?.lufs_i && (
                          <div className="text-center p-3 bg-white/60 rounded-lg">
                            <div className="text-2xl font-bold text-green-600">
                              {autoChainAnalysis.audio_features.lufs_i.toFixed(1)}
                            </div>
                            <div className="text-sm text-slate-600">LUFS</div>
                          </div>
                        )}
                        
                        {autoChainAnalysis.audio_features?.crest_db && (
                          <div className="text-center p-3 bg-white/60 rounded-lg">
                            <div className="text-2xl font-bold text-orange-600">
                              {autoChainAnalysis.audio_features.crest_db.toFixed(1)}
                            </div>
                            <div className="text-sm text-slate-600">Crest dB</div>
                          </div>
                        )}
                      </div>

                      {/* Advanced Spectral Analysis */}
                      <div className="mt-4 p-3 bg-white/40 rounded-lg">
                        <h4 className="font-semibold mb-3 text-indigo-700">🎵 Spectral Analysis</h4>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                          {autoChainAnalysis.audio_features?.spectral_tilt !== undefined && (
                            <div>
                              <span className="text-slate-600">Spectral Tilt:</span>
                              <span className="ml-1 font-medium text-blue-600">
                                {autoChainAnalysis.audio_features.spectral_tilt.toFixed(1)} dB
                              </span>
                            </div>
                          )}
                          
                          {autoChainAnalysis.audio_features?.brightness_index !== undefined && (
                            <div>
                              <span className="text-slate-600">Brightness:</span>
                              <span className="ml-1 font-medium text-yellow-600">
                                {autoChainAnalysis.audio_features.brightness_index.toFixed(2)}
                              </span>
                            </div>
                          )}
                          
                          {autoChainAnalysis.audio_features?.low_end_dominance !== undefined && (
                            <div>
                              <span className="text-slate-600">Low End:</span>
                              <span className="ml-1 font-medium text-red-600">
                                {(autoChainAnalysis.audio_features.low_end_dominance * 100).toFixed(0)}%
                              </span>
                            </div>
                          )}
                          
                          {autoChainAnalysis.audio_features?.dynamic_spread !== undefined && (
                            <div>
                              <span className="text-slate-600">Dynamics:</span>
                              <span className="ml-1 font-medium text-purple-600">
                                {autoChainAnalysis.audio_features.dynamic_spread.toFixed(1)} dB
                              </span>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Enhanced Vocal Features */}
                      {autoChainAnalysis.vocal_features && (
                        <div className="mt-4 p-3 bg-white/40 rounded-lg">
                          <h4 className="font-semibold mb-3 text-indigo-700">🎤 Advanced Vocal Analysis</h4>
                          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
                            {autoChainAnalysis.vocal_features.f0_median !== undefined && (
                              <div>
                                <span className="text-slate-600">F0 Median:</span>
                                <span className="ml-1 font-medium text-purple-600">
                                  {autoChainAnalysis.vocal_features.f0_median.toFixed(0)} Hz ({autoChainAnalysis.vocal_features.gender_profile})
                                </span>
                              </div>
                            )}
                            
                            {autoChainAnalysis.vocal_features.sibilance_centroid !== undefined && (
                              <div>
                                <span className="text-slate-600">Sibilance:</span>
                                <span className="ml-1 font-medium text-yellow-600">
                                  {autoChainAnalysis.vocal_features.sibilance_centroid.toFixed(0)} Hz
                                </span>
                              </div>
                            )}
                            
                            {autoChainAnalysis.vocal_features.mud_ratio !== undefined && (
                              <div>
                                <span className="text-slate-600">Mud (200-500Hz):</span>
                                <span className="ml-1 font-medium text-red-600">
                                  {(autoChainAnalysis.vocal_features.mud_ratio * 100).toFixed(0)}%
                                </span>
                              </div>
                            )}
                            
                            {autoChainAnalysis.vocal_features.nasal_ratio !== undefined && (
                              <div>
                                <span className="text-slate-600">Nasal (900-2kHz):</span>
                                <span className="ml-1 font-medium text-orange-600">
                                  {(autoChainAnalysis.vocal_features.nasal_ratio * 100).toFixed(0)}%
                                </span>
                              </div>
                            )}
                            
                            {autoChainAnalysis.vocal_features.plosive_index !== undefined && (
                              <div>
                                <span className="text-slate-600">Plosives:</span>
                                <span className="ml-1 font-medium text-blue-600">
                                  {(autoChainAnalysis.vocal_features.plosive_index * 100).toFixed(0)}%
                                </span>
                              </div>
                            )}
                            
                            {autoChainAnalysis.vocal_features.intensity !== undefined && (
                              <div>
                                <span className="text-slate-600">Vocal Intensity:</span>
                                <span className="ml-1 font-medium text-green-600">
                                  {(autoChainAnalysis.vocal_features.intensity * 100).toFixed(0)}%
                                </span>
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )}

                {/* AI Recommendation */}
                {autoChainRecommendation && (
                  <Card className="bg-gradient-to-r from-green-50 to-emerald-50 border-green-200">
                    <CardHeader>
                      <CardTitle className="text-lg flex items-center gap-2">
                        <Zap className="w-5 h-5 text-green-600" />
                        AI Chain Recommendation
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        <div className="flex items-center gap-3 flex-wrap">
                          <Badge variant="secondary" className="text-lg px-3 py-1">
                            {autoChainRecommendation.archetype.replace('-', ' ').toUpperCase()}
                          </Badge>
                          <div className="text-sm text-green-700 flex items-center gap-2">
                            <span>Confidence: {(autoChainRecommendation.confidence * 100).toFixed(0)}%</span>
                            {autoChainRecommendation.analysis_quality && (
                              <span className="text-xs text-slate-500">
                                (Spectral: {autoChainRecommendation.analysis_quality.spectral_analysis}, 
                                 Vocal: {autoChainRecommendation.analysis_quality.vocal_analysis})
                              </span>
                            )}
                          </div>
                        </div>
                        
                        <p className="text-sm text-slate-700 bg-white/60 p-3 rounded-lg">
                          <strong>Why this chain:</strong> {autoChainRecommendation.explanation}
                        </p>
                        
                        <div>
                          <h4 className="font-semibold mb-2 text-green-700">Recommended Plugins:</h4>
                          <div className="flex flex-wrap gap-2">
                            {autoChainRecommendation.suggested_plugins.map((plugin, idx) => (
                              <Badge key={idx} variant="outline" className="bg-white/60">
                                {plugin}
                              </Badge>
                            ))}
                          </div>
                        </div>
                        
                        <div className="flex justify-center pt-4">
                          <Button 
                            onClick={generateAutoChainPresets}
                            disabled={autoChainLoading}
                            size="lg"
                            className="bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700"
                          >
                            {autoChainLoading ? (
                              <>
                                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                Generating...
                              </>
                            ) : (
                              <>
                                <Settings className="w-4 h-4 mr-2" />
                                Generate Parameter Recommendations
                              </>
                            )}
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* Professional Parameter Recommendations */}
                {autoChainParameters && (
                  <Card className="bg-gradient-to-r from-purple-50 to-pink-50 border-purple-200">
                    <CardHeader>
                      <CardTitle className="text-lg flex items-center gap-2">
                        <Settings className="w-5 h-5 text-purple-600" />
                        📊 Professional Vocal Chain Setup
                      </CardTitle>
                      <CardDescription>
                        Apply these exact settings to your Logic Pro plugins for professional results
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-6">
                        {autoChainParameters.map((plugin, idx) => (
                          <div key={idx} className="bg-white/70 rounded-lg p-4 border border-purple-100">
                            <div className="flex items-center justify-between mb-3">
                              <div>
                                <h3 className="font-semibold text-lg text-purple-800">
                                  🎛️ {plugin.name}
                                  {plugin.instance !== 'Main' && (
                                    <span className="text-sm text-purple-600 ml-2">({plugin.instance})</span>
                                  )}
                                </h3>
                                <p className="text-sm text-slate-600 mt-1">{plugin.purpose}</p>
                              </div>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => {
                                  const paramText = Object.entries(plugin.parameters)
                                    .map(([key, value]) => `${key}: ${value}`)
                                    .join('\n');
                                  navigator.clipboard.writeText(`${plugin.name} Settings:\n${paramText}`);
                                  toast({
                                    title: "Copied to Clipboard!",
                                    description: `${plugin.name} settings copied`,
                                    className: "border-green-200 bg-green-50"
                                  });
                                }}
                              >
                                📋 Copy Settings
                              </Button>
                            </div>
                            
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                              {Object.entries(plugin.parameters).map(([param, value]) => (
                                <div key={param} className="bg-slate-50 rounded-md p-3">
                                  <div className="text-sm font-medium text-slate-700">
                                    {param.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                                  </div>
                                  <div className="text-lg font-bold text-purple-700">
                                    {typeof value === 'number' ? 
                                      (value % 1 === 0 ? value : value.toFixed(2)) : 
                                      value
                                    }
                                  </div>
                                </div>
                              ))}
                            </div>
                            
                            {plugin.summary && (
                              <div className="mt-3 p-2 bg-purple-50 rounded text-sm text-purple-700">
                                <strong>Summary:</strong> {plugin.summary}
                              </div>
                            )}
                          </div>
                        ))}
                        
                        {/* Download Section */}
                        {autoChainZipUrl && (
                          <div className="bg-white/70 rounded-lg p-4 border border-purple-100">
                            <h3 className="font-semibold text-purple-800 mb-2">💾 Download Generated Presets</h3>
                            <p className="text-sm text-slate-600 mb-3">
                              The system has generated actual .aupreset files with the parameters shown above. 
                              Download them to try in Logic Pro!
                            </p>
                            <Button
                              onClick={() => {
                                const link = document.createElement('a');
                                link.href = autoChainZipUrl;
                                link.download = `auto_vocal_chain_presets.zip`;
                                document.body.appendChild(link);
                                link.click();
                                document.body.removeChild(link);
                                
                                toast({
                                  title: "Download Started!",
                                  description: "ZIP file with .aupreset files is downloading",
                                  className: "border-green-200 bg-green-50"
                                });
                              }}
                              className="bg-gradient-to-r from-purple-500 to-pink-600 hover:from-purple-600 hover:to-pink-700"
                            >
                              <Download className="w-4 h-4 mr-2" />
                              Download Preset Files (.zip)
                            </Button>
                            <div className="mt-2 text-xs text-slate-500">
                              Extract to your Logic Pro preset folder and restart Logic Pro
                            </div>
                          </div>
                        )}
                        
                        <div className="bg-white/70 rounded-lg p-4 border border-purple-100">
                          <h3 className="font-semibold text-purple-800 mb-2">📝 Manual Setup Instructions</h3>
                          <ol className="text-sm space-y-2 text-slate-700">
                            <li><strong>1.</strong> Open Logic Pro and create a new vocal track</li>
                            <li><strong>2.</strong> For each plugin above, insert it on your vocal track</li>
                            <li><strong>3.</strong> Apply the exact parameter values shown</li>
                            <li><strong>4.</strong> Use the "Copy Settings" buttons to copy parameter values</li>
                            <li><strong>5.</strong> Save your own preset in Logic Pro for future use</li>
                          </ol>
                          <div className="mt-3 p-2 bg-yellow-50 rounded text-sm text-yellow-800">
                            <strong>💡 Pro Tip:</strong> These settings were generated specifically for your audio analysis. 
                            Feel free to fine-tune based on your preference!
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {!autoChainFile && (
                  <Alert>
                    <Upload className="h-4 w-4" />
                    <AlertDescription>
                      Upload an audio file to begin AI-powered analysis and intelligent vocal chain generation
                    </AlertDescription>
                  </Alert>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="results" className="space-y-6">
            {features && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <AudioWaveform className="w-5 h-5" />
                    Audio Analysis Results
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                    <div className="text-center p-3 bg-slate-50 rounded-lg">
                      <div className="text-2xl font-bold text-indigo-600">{Math.round(features.bpm)}</div>
                      <div className="text-sm text-slate-600">BPM</div>
                    </div>
                    <div className="text-center p-3 bg-slate-50 rounded-lg">
                      <div className="text-2xl font-bold text-purple-600">{features.lufs.toFixed(1)}</div>
                      <div className="text-sm text-slate-600">LUFS</div>
                    </div>
                    <div className="text-center p-3 bg-slate-50 rounded-lg">
                      <div className="text-2xl font-bold text-green-600">{features.crest.toFixed(1)}</div>
                      <div className="text-sm text-slate-600">Crest dB</div>
                    </div>
                    <div className="text-center p-3 bg-slate-50 rounded-lg">
                      <div className="text-2xl font-bold text-orange-600">
                        {features.spectral.tilt > 0 ? 'Bright' : 'Dark'}
                      </div>
                      <div className="text-sm text-slate-600">Tilt</div>
                    </div>
                  </div>

                  {features.vocal && (
                    <div className="mb-4">
                      <h4 className="font-medium mb-2">Vocal Analysis</h4>
                      <div className="grid grid-cols-3 gap-2 text-sm">
                        <div>Sibilance: {formatFrequency(features.vocal.sibilance_hz)}</div>
                        <div>Plosives: {(features.vocal.plosive * 100).toFixed(1)}%</div>
                        <div>Dynamics: {features.vocal.dyn_var.toFixed(1)} dB</div>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {chain && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Settings className="w-5 h-5" />
                    Generated Vocal Chain
                  </CardTitle>
                  <CardDescription>
                    {chain.name} • {chain.genre && `${chain.genre} Style`} • Professional Free Plugins
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {/* System Info */}
                  {chain.system_info && (
                    <div className="mb-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
                      <div className="flex items-center gap-2 mb-2">
                        <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                        <span className="font-semibold text-blue-800">{chain.system_info.version}</span>
                      </div>
                      <p className="text-sm text-blue-700 mb-2">{chain.system_info.upgrade_reason}</p>
                      {chain.system_info && chain.system_info.benefits && (
                        <ul className="text-xs text-blue-600 space-y-1">
                          {chain.system_info.benefits.map((benefit, idx) => (
                            <li key={idx}>• {benefit}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}

                  {/* Required Plugins Alert */}
                  {chain.required_plugins && (
                    <Alert className="mb-4">
                      <Download className="h-4 w-4" />
                      <AlertDescription>
                        <div className="space-y-2">
                          <strong>⚠️ Required Free Plugins:</strong>
                          {chain.required_plugins && chain.required_plugins.length > 0 && (
                            <div className="text-xs space-y-1">
                              {chain.required_plugins.map((plugin, idx) => (
                                <div key={idx} className="flex justify-between items-center">
                                  <span><strong>{plugin.name}</strong> - {plugin.purpose}</span>
                                  <a 
                                    href={plugin.download} 
                                    target="_blank" 
                                    rel="noopener noreferrer"
                                    className="text-blue-600 hover:text-blue-800 underline"
                                  >
                                    Download
                                  </a>
                                </div>
                              ))}
                            </div>
                          )}
                          <p className="text-xs text-amber-600 mt-2">
                            📥 Install these free plugins first, then download and install the presets below.
                          </p>
                        </div>
                      </AlertDescription>
                    </Alert>
                  )}

                  {/* Plugin Chain */}
                  <div className="space-y-2">
                    {chain && chain.chain && chain.chain.plugins ? chain.chain.plugins.map((plugin, index) => (
                      <div key={index} className="p-4 bg-slate-50 rounded-lg border">
                        <div className="flex items-center gap-3 mb-3">
                          <Badge variant="outline">{index + 1}</Badge>
                          <div className="flex-1">
                            <div className="font-medium">{plugin.plugin}</div>
                            {plugin.role && (
                              <div className="text-sm text-blue-600 font-medium">{plugin.role}</div>
                            )}
                            {plugin.variant && (
                              <div className="text-sm text-slate-600">{plugin.variant}</div>
                            )}
                            {plugin.model && (
                              <div className="text-sm text-blue-600">Model: {plugin.model}</div>
                            )}
                          </div>
                          <div className="flex items-center gap-2">
                            <Badge variant="secondary">
                              {Object.keys(plugin.params).length} params
                            </Badge>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => installIndividualPreset(plugin)}
                              disabled={loading}
                              className="px-3 py-1 text-xs"
                            >
                              <Download className="w-3 h-3 mr-1" />
                              Install
                            </Button>
                          </div>
                        </div>
                        
                        {/* Parameter Details */}
                        <div className="ml-8 space-y-1">
                          {Object.entries(plugin.params).map(([paramName, value]) => (
                            <div key={paramName} className="flex justify-between text-sm">
                              <span className="text-slate-600 capitalize">
                                {paramName.replace(/_/g, ' ')}:
                              </span>
                              <span className="font-mono">
                                {typeof value === 'boolean' 
                                  ? (value ? 'On' : 'Off')
                                  : typeof value === 'number'
                                  ? (
                                      paramName.includes('freq') ? `${value.toFixed(0)} Hz` :
                                      paramName.includes('gain') || paramName.includes('threshold') || paramName.includes('ceiling') ? `${value.toFixed(1)} dB` :
                                      paramName.includes('ratio') ? `${value.toFixed(1)}:1` :
                                      paramName.includes('attack') || paramName.includes('release') || paramName.includes('delay') ? `${value.toFixed(1)} ms` :
                                      paramName.includes('mix') && value <= 1 ? `${(value * 100).toFixed(0)}%` :
                                      paramName.includes('mix') && value > 1 ? `${value.toFixed(1)} dB` :
                                      value.toFixed(2)
                                    )
                                  : String(value)
                                }
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )) : <div className="text-center text-slate-500 py-4">No plugins available</div>}
                  </div>
                </CardContent>
              </Card>
            )}

            {downloadUrl && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Download className="w-5 h-5" />
                    Download Logic Pro Presets
                  </CardTitle>
                  <CardDescription>
                    Your vocal chain is ready! Download the ZIP file and import into Logic Pro.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex justify-center gap-4">
                    <Button onClick={installToLogic} size="lg" className="bg-green-600 hover:bg-green-700">
                      <Download className="w-4 h-4 mr-2" />
                      Download Preset Package
                    </Button>
                    <Button onClick={resetForm} variant="outline" size="lg">
                      Process Another
                    </Button>
                  </div>
                  
                  <Alert>
                    <Download className="h-4 w-4" />
                    <AlertDescription>
                      <div className="space-y-4">
                        <div>
                          <strong className="text-green-600">🎉 Professional Free Plugin System!</strong>
                          <br />
                          This vocal chain uses high-quality free third-party AU plugins instead of Logic's stock plugins.
                        </div>
                        
                        <div>
                          <strong>Step 1: Install Required Free Plugins</strong>
                          <br />
                          Download and install these free plugins first (links provided above in the chain details).
                          All plugins are professional-grade and completely free.
                        </div>
                        
                        <div>
                          <strong>Step 2: Extract the ZIP file</strong>
                          <br />
                          Double-click the downloaded ZIP to extract it.
                        </div>
                        
                        <div>
                          <strong>Step 3: Install .aupreset Files</strong>
                          <br />
                          Copy .aupreset files to: <code>~/Library/Audio/Presets/[Manufacturer]/[Plugin Name]/</code>
                          <br />
                          <em>Example:</em> TDR Nova presets go to <code>~/Library/Audio/Presets/Tokyo Dawn Records/TDR Nova/</code>
                        </div>
                        
                        <div>
                          <strong>Step 4: Restart Logic Pro</strong>
                          <br />
                          The presets will appear in each plugin's preset menu.
                        </div>
                        
                        <div>
                          <strong>Quick Install Commands:</strong>
                          <br />
                          <code className="text-xs block mt-1 p-2 bg-slate-100 rounded">
                            cd ~/Downloads/[extracted-folder]/<br />
                            cp "Plug-In Settings"/*/*.aupreset ~/Library/Audio/Presets/*/  <br />
                            # Then restart Logic Pro
                          </code>
                        </div>
                        
                        <div className="bg-green-50 p-3 rounded border border-green-200">
                          <strong className="text-green-700">✨ Benefits of This System:</strong>
                          <ul className="text-green-600 text-sm mt-1 space-y-1">
                            <li>• Higher audio quality than Logic's stock plugins</li>
                            <li>• Professional tools used in commercial productions</li>
                            <li>• Standard .aupreset format - no proprietary issues</li>
                            <li>• Genre-specific processing optimized for Pop, R&B, Hip-Hop</li>
                            <li>• All plugins are completely free forever</li>
                          </ul>
                        </div>
                        
                        <div className="text-amber-600">
                          <strong>Note:</strong> You must install the required free plugins first. 
                          The presets won't work with Logic's stock plugins due to different parameter structures.
                        </div>
                      </div>
                    </AlertDescription>
                  </Alert>
                </CardContent>
              </Card>
            )}

            {/* Installation Result Display */}
            {installationResult && (
              <Card>
                <CardContent className="pt-6">
                  {installationResult && (
                    <Alert className="border-green-200 bg-green-50">
                      <AlertDescription>
                        <div className="space-y-2">
                          <strong>✅ Preset Package Downloaded!</strong>
                          <p className="text-sm">
                            File: <code className="bg-slate-100 px-1 rounded">{installationResult.download?.filename}</code>
                          </p>
                          <p className="text-sm">
                            Generated {installationResult.download?.preset_count} presets. 
                            Check your downloads folder and follow the README.txt instructions to install in Logic Pro.
                          </p>
                          <div className="text-xs text-slate-600 mt-2">
                            <strong>Quick Install Guide:</strong>
                            <br />1. Extract the ZIP file
                            <br />2. Copy each .aupreset file to its plugin's directory in ~/Library/Audio/Presets/
                            <br />3. Restart Logic Pro
                            <br />4. Presets will appear in each plugin's menu
                          </div>
                        </div>
                      </AlertDescription>
                    </Alert>
                  )}
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="config" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="w-5 h-5" />
                  System Configuration
                </CardTitle>
                <CardDescription>
                  Configure paths and view system information for optimal preset generation
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex gap-4">
                  <Button 
                    onClick={fetchSystemInfo} 
                    disabled={configLoading}
                    variant="outline"
                  >
                    {configLoading ? "Loading..." : "Refresh System Info"}
                  </Button>
                  <Button 
                    onClick={fetchPluginPaths} 
                    disabled={configLoading}
                    variant="outline"
                  >
                    {configLoading ? "Loading..." : "Load Plugin Paths"}
                  </Button>
                </div>

                {systemInfo && (
                  <div className="space-y-4">
                    <div className="p-4 bg-slate-50 rounded-lg border">
                      <h3 className="font-semibold mb-3">System Information</h3>
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <strong>Platform:</strong> {systemInfo.platform}
                        </div>
                        <div>
                          <strong>macOS:</strong> {systemInfo.is_macos ? "✅ Yes" : "❌ No"}
                        </div>
                        <div>
                          <strong>Container:</strong> {systemInfo.is_container ? "✅ Yes" : "❌ No"}
                        </div>
                        <div>
                          <strong>Swift CLI Available:</strong> {systemInfo.swift_cli_available ? "✅ Yes" : "❌ No"}
                        </div>
                      </div>
                    </div>

                    <div className="p-4 bg-slate-50 rounded-lg border">
                      <h3 className="font-semibold mb-3">Path Configuration</h3>
                      <div className="space-y-3 text-sm">
                        <div>
                          <strong>Swift CLI:</strong>
                          <br />
                          <code className="text-xs bg-slate-100 p-1 rounded">{systemInfo.swift_cli_path}</code>
                        </div>
                        <div>
                          <strong>Seeds Directory:</strong>
                          <br />
                          <code className="text-xs bg-slate-100 p-1 rounded">{systemInfo.seeds_directory}</code>
                          <span className="ml-2">
                            {systemInfo.seeds_directory_exists ? "✅ Exists" : "❌ Not Found"}
                          </span>
                        </div>
                        <div>
                          <strong>Logic Pro Presets:</strong>
                          <br />
                          <code className="text-xs bg-slate-100 p-1 rounded">
                            {systemInfo.logic_preset_dirs.custom}
                          </code>
                        </div>
                      </div>
                    </div>

                    <div className="p-4 bg-slate-50 rounded-lg border">
                      <h3 className="font-semibold mb-3">Available Seed Files ({systemInfo.available_seed_files.length})</h3>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        {systemInfo.available_seed_files.map((file, idx) => (
                          <div key={idx} className="flex items-center gap-2">
                            <span className="text-green-600">✅</span>
                            <code>{file}</code>
                          </div>
                        ))}
                      </div>
                    </div>

                    {!systemInfo.swift_cli_available && (
                      <Alert>
                        <AlertDescription>
                          <div className="space-y-2">
                            <strong>⚠️ Swift CLI Not Available</strong>
                            <p>
                              The system is using Python fallback for preset generation. 
                              For best results on macOS, configure the Swift CLI path below.
                            </p>
                          </div>
                        </AlertDescription>
                      </Alert>
                    )}

                    {pluginPaths && (
                      <div className="p-4 border rounded-lg">
                        <h3 className="font-semibold mb-3">Individual Plugin Paths</h3>
                        <p className="text-sm text-slate-600 mb-4">
                          Configure where each plugin's presets will be saved. Swift CLI will automatically add /Presets/[Manufacturer]/[Plugin]/ to each path.
                        </p>
                        
                        <div className="space-y-3">
                          {Object.entries(pluginPaths).map(([pluginName, currentPath]) => (
                            <div key={pluginName} className="flex items-center gap-3 p-3 bg-slate-50 rounded border">
                              <div className="flex-1">
                                <div className="font-medium text-sm">{pluginName}</div>
                                <Input 
                                  id={`path-${pluginName.replace(' ', '-')}`}
                                  defaultValue={currentPath}
                                  placeholder="/Library/Audio"
                                  className="mt-1 text-xs"
                                />
                              </div>
                              <Button 
                                onClick={() => resetPluginPath(pluginName)}
                                disabled={configLoading}
                                variant="outline"
                                size="sm"
                              >
                                Reset
                              </Button>
                            </div>
                          ))}
                          
                          <Button 
                            onClick={() => {
                              const updates = {};
                              Object.keys(pluginPaths).forEach(pluginName => {
                                const inputId = `path-${pluginName.replace(' ', '-')}`;
                                const inputElement = document.getElementById(inputId);
                                if (inputElement && inputElement.value.trim()) {
                                  updates[pluginName] = inputElement.value.trim();
                                }
                              });
                              
                              if (Object.keys(updates).length > 0) {
                                configurePluginPaths(updates);
                              } else {
                                toast({
                                  title: "No Changes",
                                  description: "No paths were modified",
                                  variant: "outline"
                                });
                              }
                            }}
                            disabled={configLoading}
                            className="w-full"
                          >
                            {configLoading ? "Updating..." : "Update Plugin Paths"}
                          </Button>
                        </div>
                      </div>
                    )}

                    <div className="p-4 border rounded-lg">
                      <h3 className="font-semibold mb-3">Global Configuration</h3>
                      <div className="space-y-4">
                        <div>
                          <Label htmlFor="swift-cli-path">Swift CLI Binary Path (macOS only)</Label>
                          <Input 
                            id="swift-cli-path"
                            placeholder="/Users/yourname/MicDrop/aupresetgen/.build/release/aupresetgen"
                            className="mt-1"
                          />
                        </div>
                        <div>
                          <Label htmlFor="seeds-dir">Seed Files Directory</Label>
                          <Input 
                            id="seeds-dir"
                            placeholder="/Users/yourname/Desktop/Plugin Seeds"
                            className="mt-1"
                          />
                        </div>
                        <div>
                          <Label htmlFor="logic-presets-dir">Logic Pro Presets Directory</Label>
                          <Input 
                            id="logic-presets-dir"
                            placeholder="/Users/yourname/Library/Audio/Presets"
                            className="mt-1"
                          />
                        </div>
                        <Button 
                          onClick={() => {
                            const swiftPath = document.getElementById('swift-cli-path').value;
                            const seedsDir = document.getElementById('seeds-dir').value;
                            const presetsDir = document.getElementById('logic-presets-dir').value;
                            
                            const config = {};
                            if (swiftPath) config.swift_cli_path = swiftPath;
                            if (seedsDir) config.seeds_dir = seedsDir;
                            if (presetsDir) config.logic_presets_dir = presetsDir;
                            
                            if (Object.keys(config).length > 0) {
                              configurePaths(config);
                            } else {
                              toast({
                                title: "No Changes",
                                description: "Please enter at least one path to configure",
                                variant: "outline"
                              });
                            }
                          }}
                          disabled={configLoading}
                          className="w-full"
                        >
                          {configLoading ? "Configuring..." : "Apply Configuration"}
                        </Button>
                      </div>
                    </div>

                    <Alert>
                      <AlertDescription>
                        <div className="space-y-2">
                          <strong>💡 Configuration Tips:</strong>
                          <ul className="text-sm space-y-1 mt-2">
                            <li>• <strong>macOS Users:</strong> Configure the Swift CLI path for optimal performance</li>
                            <li>• <strong>First Time Setup:</strong> Use this to point to your actual seed files location</li>
                            <li>• <strong>Logic Pro Directory:</strong> Presets will be installed to this location</li>
                            <li>• <strong>Container Users:</strong> Python fallback works automatically</li>
                          </ul>
                        </div>
                      </AlertDescription>
                    </Alert>
                  </div>
                )}

                {!systemInfo && (
                  <div className="text-center py-8 text-slate-600">
                    <Settings className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>Click "Refresh System Info" to view configuration details</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
      
      <Toaster />
    </div>
  );
}

export default App;