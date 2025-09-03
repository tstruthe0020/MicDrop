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

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
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
  
  const beatInputRef = useRef(null);
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
    if (!beatFile) {
      toast({ 
        title: "Missing beat file", 
        description: "Please upload a beat file to continue",
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
      const formData = new FormData();
      formData.append('beat_file', beatFile);
      if (vocalFile) {
        formData.append('vocal_file', vocalFile);
      }
      formData.append('preset_name', presetName);
      formData.append('vibe', vibe);

      // Simulate progress
      const progressInterval = setInterval(() => {
        setProgress(prev => Math.min(prev + 10, 90));
      }, 500);

      const response = await axios.post(`${API}/all-in-one`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120000 // 2 minute timeout
      });

      clearInterval(progressInterval);
      setProgress(100);

      const { features: audioFeatures, chain: vocalChain, preset_zip_base64 } = response.data;
      
      setFeatures(audioFeatures);
      setChain(vocalChain);

      // Create download URL from base64
      const binaryString = atob(preset_zip_base64);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      const blob = new Blob([bytes], { type: 'application/zip' });
      const url = URL.createObjectURL(blob);
      setDownloadUrl(url);

      setActiveTab('results');
      
      toast({ 
        title: "Processing complete!", 
        description: "Your vocal chain preset is ready for download" 
      });

    } catch (error) {
      console.error('Processing failed:', error);
      toast({ 
        title: "Processing failed", 
        description: error.response?.data?.detail || "An error occurred during processing",
        variant: "destructive" 
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const installToLogic = async () => {
    if (!chain || !vibe) return;
    
    setLoading(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/export/install-to-logic`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          vibe: vibe,
          genre: null, // Can be extended later
          audio_type: null // Can be extended later
        })
      });
      
      const result = await response.json();
      
      if (result.success) {
        toast({
          title: "🎵 Presets Installed!",
          description: result.message,
          className: "border-green-200 bg-green-50"
        });
        
        // Show detailed instructions
        setInstallationResult(result);
      } else {
        toast({
          title: "Installation Failed",
          description: result.message,
          variant: "destructive"
        });
      }
    } catch (error) {
      console.error('Installation error:', error);
      toast({
        title: "Installation Error",
        description: "Failed to install presets to Logic Pro",
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
          <TabsList className="grid w-full grid-cols-4 mb-8">
            <TabsTrigger value="upload" className="flex items-center gap-2">
              <Upload className="w-4 h-4" />
              Upload & Configure
            </TabsTrigger>
            <TabsTrigger value="process" className="flex items-center gap-2">
              <Settings className="w-4 h-4" />
              Process
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
                    disabled={!beatFile || isProcessing}
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

                {!beatFile && (
                  <Alert>
                    <Upload className="h-4 w-4" />
                    <AlertDescription>
                      Upload a beat file to enable processing
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
                      {chain.system_info.benefits && (
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
                          <p className="text-xs text-amber-600 mt-2">
                            📥 Install these free plugins first, then download and install the presets below.
                          </p>
                        </div>
                      </AlertDescription>
                    </Alert>
                  )}

                  {/* Plugin Chain */}
                  <div className="space-y-2">
                    {chain.plugins.map((plugin, index) => (
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
                    ))}
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
                      Install to Logic Pro
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
          </TabsContent>
        </Tabs>
      </div>
      
      <Toaster />
    </div>
  );
}

export default App;