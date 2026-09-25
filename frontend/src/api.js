// Thin wrapper around the backend API. Every failure is converted into an
// ApiError whose message is safe to show directly to the customer.

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const REQUEST_TIMEOUT_MS = 45_000;

export class ApiError extends Error {}

async function readErrorDetail(response) {
  try {
    const body = await response.json();
    return typeof body.detail === "string" ? body.detail : null;
  } catch {
    return null;
  }
}

export async function sendChatMessage(message, conversationId) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  let response;
  try {
    response = await fetch(`${API_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, conversation_id: conversationId }),
      signal: controller.signal,
    });
  } catch (err) {
    throw new ApiError(
      err.name === "AbortError"
        ? "The request timed out. Please try again."
        : "We can't reach the support server right now. Please check that the backend is running and try again."
    );
  } finally {
    clearTimeout(timer);
  }

  if (!response.ok) {
    const detail = await readErrorDetail(response);
    if (response.status === 503) {
      throw new ApiError(detail ?? "The support assistant is temporarily unavailable. Please try again shortly.");
    }
    if (response.status === 422) {
      throw new ApiError("That message couldn't be processed. Please keep it under 2,000 characters.");
    }
    throw new ApiError("Something went wrong on our end. Please try again in a moment.");
  }

  return response.json();
}
