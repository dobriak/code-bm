import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import './index.css'
import App from './App.tsx'
import AdminScanPanel from './pages/AdminScanPanel.tsx'
import AdminLoginPage from './pages/AdminLoginPage.tsx'
import AdminDashboard from './pages/AdminDashboard.tsx'
import AdminSettings from './pages/AdminSettings.tsx'
import AdminQueue from './pages/AdminQueue.tsx'
import BrowsePage from './pages/BrowsePage.tsx'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60,
      retry: 1,
    },
  },
})

function AdminRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem("raidio.admin_jwt")
  if (!token) {
    return <Navigate to="/admin/login" replace />
  }
  return <>{children}</>
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<App />} />
          <Route path="/admin/login" element={<AdminLoginPage />} />
          <Route path="/admin" element={
            <AdminRoute>
              <AdminScanPanel />
            </AdminRoute>
          } />
          <Route path="/admin/dashboard" element={
            <AdminRoute>
              <AdminDashboard />
            </AdminRoute>
          } />
          <Route path="/admin/settings" element={
            <AdminRoute>
              <AdminSettings />
            </AdminRoute>
          } />
          <Route path="/admin/queue" element={
            <AdminRoute>
              <AdminQueue />
            </AdminRoute>
          } />
          <Route path="/browse" element={<BrowsePage />} />
          <Route path="/create" element={<BrowsePage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)