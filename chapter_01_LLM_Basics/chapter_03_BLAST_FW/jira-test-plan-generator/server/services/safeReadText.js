export async function safeReadText(response) {
  try {
    return await response.text();
  } catch {
    return '';
  }
}
