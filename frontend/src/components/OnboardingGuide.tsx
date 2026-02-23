import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Radar, Upload, Brain, Search, BookOpen, X } from "lucide-react";

const STEPS = [
    { icon: Upload, titleKey: "onboarding.step1Title", descKey: "onboarding.step1Desc" },
    { icon: Brain, titleKey: "onboarding.step2Title", descKey: "onboarding.step2Desc" },
    { icon: Search, titleKey: "onboarding.step3Title", descKey: "onboarding.step3Desc" },
    { icon: Radar, titleKey: "onboarding.step4Title", descKey: "onboarding.step4Desc" },
    { icon: BookOpen, titleKey: "onboarding.step5Title", descKey: "onboarding.step5Desc" },
];

const OnboardingGuide = ({ onDismiss }: { onDismiss: () => void }) => {
    const { t } = useTranslation();
    const [step, setStep] = useState(0);
    const current = STEPS[step];
    const Icon = current.icon;

    return (
        <Card className="border-primary/30 bg-primary/5">
            <CardContent className="p-6">
                <div className="flex justify-between items-start mb-4">
                    <div className="flex items-center gap-3">
                        <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                            <Icon className="h-5 w-5 text-primary" />
                        </div>
                        <div>
                            <h3 className="font-semibold text-sm">{t(current.titleKey)}</h3>
                            <p className="text-xs text-muted-foreground">{step + 1} / {STEPS.length}</p>
                        </div>
                    </div>
                    <Button variant="ghost" size="sm" onClick={onDismiss}><X className="h-4 w-4" /></Button>
                </div>
                <p className="text-sm text-muted-foreground mb-4">{t(current.descKey)}</p>
                <div className="flex gap-2">
                    {step > 0 && <Button variant="outline" size="sm" onClick={() => setStep(step - 1)}>{t("onboarding.prev")}</Button>}
                    {step < STEPS.length - 1 ? (
                        <Button size="sm" onClick={() => setStep(step + 1)}>{t("onboarding.next")}</Button>
                    ) : (
                        <Button size="sm" onClick={onDismiss}>{t("onboarding.done")}</Button>
                    )}
                    <div className="flex-1" />
                    <div className="flex gap-1 items-center">
                        {STEPS.map((_, i) => (
                            <div key={i} className={`h-1.5 w-1.5 rounded-full ${i === step ? "bg-primary" : "bg-muted-foreground/30"}`} />
                        ))}
                    </div>
                </div>
            </CardContent>
        </Card>
    );
};

export default OnboardingGuide;
