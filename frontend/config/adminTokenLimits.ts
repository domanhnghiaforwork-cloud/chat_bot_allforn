export interface TokenDraftState {
  drafts: Record<string, string | boolean>;
  pendingResets: Record<string, boolean>;
}

export function adjustTokenDrafts(state: TokenDraftState): TokenDraftState {
  const maximum = Number(state.drafts.MAX_CONVERSATION_TOKENS);
  const context = Number(state.drafts.CHAT_CONTEXT_WINDOW_TOKENS);
  // Cho phép nhập dở; chỉ giảm context khi trần mới là số nguyên hợp lệ.
  if (!Number.isSafeInteger(maximum) || maximum < 100 || context <= maximum || !Number.isFinite(context)) {
    return state;
  }
  return {
    drafts: { ...state.drafts, CHAT_CONTEXT_WINDOW_TOKENS: String(maximum) },
    pendingResets: { ...state.pendingResets, CHAT_CONTEXT_WINDOW_TOKENS: false },
  };
}
