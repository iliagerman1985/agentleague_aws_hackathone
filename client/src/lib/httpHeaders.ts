export function buildApiHeaders(
  body: RequestInit["body"],
  incomingHeaders: HeadersInit | undefined,
  token: string | null,
): Record<string, string> {
  const headers: Record<string, string> = {};

  if (incomingHeaders instanceof Headers) {
    incomingHeaders.forEach((value, key) => {
      headers[key] = value;
    });
  } else if (Array.isArray(incomingHeaders)) {
    for (const [key, value] of incomingHeaders) {
      headers[key] = value;
    }
  } else if (incomingHeaders) {
    Object.assign(headers, incomingHeaders);
  }

  const existingContentTypeKey = Object.keys(headers).find(
    (key) => key.toLowerCase() === "content-type",
  );
  const isFormData = typeof FormData !== "undefined" && body instanceof FormData;

  if (isFormData && existingContentTypeKey) {
    delete headers[existingContentTypeKey];
  } else if (!isFormData && !existingContentTypeKey && body !== null) {
    headers["Content-Type"] = "application/json";
  }

  if (token && !Object.keys(headers).some((key) => key.toLowerCase() === "authorization")) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  return headers;
}
