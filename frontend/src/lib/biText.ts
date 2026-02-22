import i18n from "../i18n";

/**
 * 从双语字段中取当前语言的文本。
 * 兼容旧数据（纯字符串）和新数据（{en, zh} 对象）。
 */
export function biText(val: unknown): string {
    if (!val) return "";
    if (typeof val === "string") return val;
    if (typeof val === "object" && val !== null) {
        const obj = val as Record<string, string>;
        const lang = i18n.language?.startsWith("zh") ? "zh" : "en";
        return obj[lang] || obj["en"] || obj["zh"] || "";
    }
    return String(val);
}
