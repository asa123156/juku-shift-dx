// src/App.jsx
import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';

import Login from './pages/Login';
import StudentShift from './pages/StudentShift';
import StudentSchedule from './pages/StudentSchedule';
import AdminDashboard from './pages/AdminDashboard';
import AdminManage from './pages/AdminManage';
import AssignmentStudentPicker from './pages/AssignmentStudentPicker';
import AssignmentBoard from './pages/AssignmentBoard';
import DataImport from './pages/DataImport';
import ProtectedRoute from './components/ProtectedRoute';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/student" element={<ProtectedRoute roles={['teacher']}><StudentShift /></ProtectedRoute>} />
        <Route path="/student-schedule" element={<ProtectedRoute roles={['student']}><StudentSchedule /></ProtectedRoute>} />
        <Route path="/admin" element={<ProtectedRoute roles={['admin']}><AdminDashboard /></ProtectedRoute>} />
        <Route path="/admin/manage" element={<ProtectedRoute roles={['admin']}><AdminManage /></ProtectedRoute>} />
        <Route path="/admin/assignments" element={<ProtectedRoute roles={['admin']}><AssignmentStudentPicker /></ProtectedRoute>} />
        <Route path="/admin/assignments/:studentId" element={<ProtectedRoute roles={['admin']}><AssignmentBoard /></ProtectedRoute>} />
        <Route path="/import" element={<ProtectedRoute roles={['admin']}><DataImport /></ProtectedRoute>} />
      </Routes>
    </BrowserRouter>
  );
}