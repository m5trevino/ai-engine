import React from 'react';
import { PeacockAPI } from '../../lib/api';
import { Icons } from '../dashboard/MaterialIcons';

export const OnboardingPanel: React.FC = () => {
    const [name, setName] = React.useState('');
    const [description, setDescription] = React.useState('');
    const [modelPack, setModelPack] = React.useState('smart');
    const [result, setResult] = React.useState<any>(null);
    const [loading, setLoading] = React.useState(false);

    const handleOnboard = async () => {
        setLoading(true);
        try {
            const data = await PeacockAPI.onboardApp({ name, description, model_pack: modelPack });
            setResult(data);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="h-full flex flex-col p-8 space-y-8 bg-mil-charcoal overflow-y-auto">
            <div className="space-y-2">
                <h1 className="font-headline text-4xl font-bold tracking-[0.3em] glow-text-cyan">APP_ONBOARDING</h1>
                <p className="font-mono text-[10px] text-mil-olive">REGISTER A NEW NODE IN THE SYNDICATE NETWORK</p>
            </div>

            <div className="grid grid-cols-12 gap-8">
                {/* Registration Form */}
                <div className="col-span-12 lg:col-span-5 space-y-6">
                    <div className="chrome-panel p-6 space-y-4">
                        <div className="space-y-1">
                            <label className="font-headline text-[10px] text-mil-olive">APP_NAME</label>
                            <input 
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                className="w-full bg-mil-charcoal-deep border border-mil-olive-dark p-3 text-mil-cyan font-rugged outline-none focus:border-mil-cyan recessed-well"
                                placeholder="e.g. MISSION_CONTROL_X"
                            />
                        </div>

                        <div className="space-y-1">
                            <label className="font-headline text-[10px] text-mil-olive">MISSION_DESCRIPTION</label>
                            <textarea 
                                value={description}
                                onChange={(e) => setDescription(e.target.value)}
                                className="w-full bg-mil-charcoal-deep border border-mil-olive-dark p-3 text-mil-offwhite font-body outline-none focus:border-mil-cyan recessed-well h-24"
                                placeholder="Describe the operational mandate..."
                            />
                        </div>

                        <div className="space-y-1">
                            <label className="font-headline text-[10px] text-mil-olive">MODEL_PACK_TIER</label>
                            <div className="grid grid-cols-3 gap-2">
                                {['fast', 'smart', 'all'].map(t => (
                                    <button 
                                        key={t}
                                        onClick={() => setModelPack(t)}
                                        className={`py-2 font-headline text-[10px] border transition-all ${modelPack === t ? 'border-mil-cyan text-mil-cyan bg-mil-cyan/10' : 'border-mil-olive-dark text-mil-olive'}`}
                                    >
                                        {t.toUpperCase()}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <button 
                            onClick={handleOnboard}
                            disabled={!name || loading}
                            className="w-full mil-btn mil-btn-accent py-3 font-rugged text-lg tracking-widest mt-4"
                        >
                            {loading ? 'CALCULATING_HASH...' : 'ONBOARD_APPLICATION'}
                        </button>
                    </div>
                </div>

                {/* Integration Kit Display */}
                <div className="col-span-12 lg:col-span-7">
                    {result ? (
                        <div className="space-y-6 animate-in fade-in slide-in-from-right duration-500">
                             <div className="flex gap-4">
                                <div className="flex-1 recessed-well p-4 border-l-4 border-mil-cyan">
                                    <span className="font-headline text-[10px] text-mil-cyan">APP_ID</span>
                                    <p className="font-rugged text-2xl translate-y-1">{result.app_id}</p>
                                </div>
                                <div className="flex-1 recessed-well p-4 border-l-4 border-mil-magenta">
                                    <span className="font-headline text-[10px] text-mil-magenta">API_SECRET</span>
                                    <p className="font-mono text-xs mt-1 blur-sm hover:blur-none cursor-pointer transition-all">{result.api_secret}</p>
                                </div>
                             </div>

                             <div className="space-y-2">
                                <label className="font-headline text-[10px] text-mil-olive">INTEGRATION_COMMANDS</label>
                                <div className="recessed-well p-6 font-mono text-sm space-y-4">
                                    <div className="space-y-1">
                                        <p className="text-mil-cyan opacity-40 uppercase text-[9px] font-bold">// Python SDK Init</p>
                                        <code className="text-mil-offwhite block bg-black/40 p-3">{result.integration_kit.sdk_init}</code>
                                    </div>
                                    <div className="space-y-1">
                                        <p className="text-mil-magenta opacity-40 uppercase text-[9px] font-bold">// Direct Strike Curl</p>
                                        <code className="text-mil-offwhite block bg-black/40 p-3 break-all">{result.integration_kit.curl_example}</code>
                                    </div>
                                </div>
                             </div>

                             <div className="recessed-well p-4 flex items-center justify-between">
                                <span className="font-headline text-[10px] text-mil-olive">ALLOWED_MODELS</span>
                                <div className="flex gap-2">
                                    {result.allowed_models.slice(0, 3).map((m: string) => (
                                        <span key={m} className="bg-mil-olive-dark text-[9px] px-2 py-0.5 font-mono">{m}</span>
                                    ))}
                                    {result.allowed_models.length > 3 && <span className="text-[9px] opacity-40">+{result.allowed_models.length - 3} MORE</span>}
                                </div>
                             </div>
                        </div>
                    ) : (
                        <div className="h-full flex flex-col items-center justify-center space-y-4 text-mil-olive/30 recessed-well">
                            <Icons.Dashboard className="w-16 h-16 opacity-10" />
                            <p className="font-headline text-xs tracking-widest">AWAITING_REGISTRATION_PACKET</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
