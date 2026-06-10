// src/App.jsx
import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';

import Login from './pages/Login';
import StudentShift from './pages/StudentShift';
import StudentSchedule from './pages/StudentSchedule';
import AdminDashboard from './pages/AdminDashboard';
import DataImport from './pages/DataImport';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/student" element={<StudentShift />} />
        <Route path="/student-schedule" element={<StudentSchedule />} />
        <Route path="/admin" element={<AdminDashboard />} />
        <Route path="/import" element={<DataImport />} />
      </Routes>
    </BrowserRouter>
  );
}