export function fuzzyMatch(query: string, text: string): boolean {
    if (!query) return true
    const q = query.toLowerCase()
    const t = text.toLowerCase()
    let qi = 0
    for (let i = 0; i < t.length && qi < q.length; i++) {
        if (t[i] === q[qi]) qi++
    }
    return qi === q.length
}
