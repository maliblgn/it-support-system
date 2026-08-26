import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, apiRequest } from "./client";

function response({ status = 200, contentType = "application/json", payload = {} } = {}) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers({ "content-type": contentType }),
    json: vi.fn().mockResolvedValue(payload),
    blob: vi.fn().mockResolvedValue(new Blob(["dosya"])),
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
  document.cookie = "it_ticket_csrf=; Max-Age=0; path=/";
});

describe("apiRequest", () => {
  it("değişiklik isteklerine CSRF başlığını ve oturum bilgisini ekler", async () => {
    document.cookie = "it_ticket_csrf=test-token; path=/";
    const fetchMock = vi.fn().mockResolvedValue(response({ payload: { id: 7 } }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(apiRequest("/tickets", { method: "POST", body: JSON.stringify({ subject: "Test" }) }))
      .resolves.toEqual({ id: 7 });

    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/tickets");
    expect(options.credentials).toBe("include");
    expect(options.headers.get("X-CSRF-Token")).toBe("test-token");
    expect(options.headers.get("Content-Type")).toBe("application/json");
  });

  it("204 yanıtını boş sonuç olarak döndürür", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({ status: 204 })));
    await expect(apiRequest("/auth/logout", { method: "POST" })).resolves.toBeNull();
  });

  it("sunucu hatasındaki iç ayrıntıyı kullanıcıya sızdırmaz", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({
      status: 500,
      payload: { detail: "SQL bağlantı dizesi ve iç sunucu izi" },
    })));

    await expect(apiRequest("/tickets")).rejects.toMatchObject({
      name: "ApiError",
      status: 500,
      message: "İşlem sırasında beklenmeyen bir sorun oluştu. Lütfen yeniden deneyin.",
    });
  });

  it("alan doğrulama hatalarını anlaşılır biçimde özetler", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({
      status: 422,
      payload: { detail: [{ loc: ["body", "subject"], msg: "Bu alan zorunludur" }] },
    })));

    await expect(apiRequest("/tickets")).rejects.toEqual(
      expect.objectContaining({
        constructor: ApiError,
        message: "subject: Bu alan zorunludur",
      }),
    );
  });
});
