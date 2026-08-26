import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProfilePage } from "./UserPages";

const mocks = vi.hoisted(() => ({
  setUser: vi.fn(),
  updateProfile: vi.fn(),
}));

const currentUser = {
  id: 9,
  email: "ayse@company.com",
  first_name: "Ayşe",
  last_name: "Yılmaz",
  phone: null,
  department: "Finans",
  role: "USER",
};

vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({ user: currentUser, setUser: mocks.setUser }),
}));

vi.mock("../api/client", () => ({
  api: { updateProfile: mocks.updateProfile },
  saveBlob: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("profil ayarları", () => {
  it("e-postayı düzenler ve şifre yönetimini profil içinden açar", async () => {
    const updatedUser = { ...currentUser, email: "ayse.yeni@company.com" };
    mocks.updateProfile.mockResolvedValue(updatedUser);

    render(<MemoryRouter><ProfilePage /></MemoryRouter>);

    const emailInput = screen.getByLabelText(/^E-posta/);
    expect(emailInput).toBeEnabled();
    fireEvent.change(emailInput, { target: { value: updatedUser.email } });
    fireEvent.click(screen.getByRole("button", { name: "Değişiklikleri kaydet" }));

    await waitFor(() => expect(mocks.updateProfile).toHaveBeenCalledWith({
      email: updatedUser.email,
      first_name: "Ayşe",
      last_name: "Yılmaz",
      phone: null,
      department: "Finans",
    }));
    expect(mocks.setUser).toHaveBeenCalledWith(updatedUser);
    expect(screen.getByRole("link", { name: /Şifremi değiştir/i })).toHaveAttribute(
      "href",
      "/change-password",
    );
  });
});
