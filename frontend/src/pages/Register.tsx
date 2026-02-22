import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";

export default function Register() {
    const { t } = useTranslation();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleRegister = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        try {
            await api.post("/api/auth/register", { email, password });
            toast.success(t("register.success"));
            navigate("/login");
        } catch (error: any) {
            const msg = error.response?.data?.detail || t("register.failed");
            toast.error(msg);
        } finally { setLoading(false); }
    };

    return (
        <div className="flex items-center justify-center min-h-screen bg-slate-50 dark:bg-gray-950">
            <Card className="w-full max-w-md">
                <CardHeader>
                    <CardTitle className="text-2xl">{t("register.title")}</CardTitle>
                    <CardDescription>{t("register.description")}</CardDescription>
                </CardHeader>
                <form onSubmit={handleRegister}>
                    <CardContent className="space-y-4">
                        <div className="space-y-2"><Label htmlFor="email">{t("register.email")}</Label><Input id="email" type="email" placeholder="m@example.com" required value={email} onChange={(e) => setEmail(e.target.value)} /></div>
                        <div className="space-y-2"><Label htmlFor="password">{t("register.password")}</Label><Input id="password" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} /></div>
                    </CardContent>
                    <CardFooter className="flex flex-col space-y-2">
                        <Button className="w-full" type="submit" disabled={loading}>{loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}{t("register.submit")}</Button>
                        <div className="text-sm text-center text-slate-500">{t("register.hasAccount")} <Link to="/login" className="underline">{t("register.login")}</Link></div>
                    </CardFooter>
                </form>
            </Card>
        </div>
    );
}
