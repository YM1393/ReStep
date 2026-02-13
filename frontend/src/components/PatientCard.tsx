import { Link } from 'react-router-dom';
import type { Patient } from '../types';

interface PatientCardProps {
  patient: Patient;
}

export default function PatientCard({ patient }: PatientCardProps) {
  const age = calculateAge(patient.birth_date);

  return (
    <Link
      to={`/patients/${patient.id}`}
      className="patient-card flex items-center space-x-4 block"
    >
      {/* 아바타 */}
      <div className={`avatar ${patient.gender === 'M' ? 'from-blue-400 to-blue-600' : 'from-pink-400 to-pink-600'}`}>
        {patient.name.charAt(0)}
      </div>

      {/* 정보 */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center space-x-2">
          <h3 className="font-semibold text-gray-800 dark:text-gray-100 truncate">{patient.name}</h3>
          <span className={`badge ${patient.gender === 'M' ? 'badge-blue' : 'bg-pink-100 dark:bg-pink-900/50 text-pink-600 dark:text-pink-400'}`}>
            {patient.gender === 'M' ? '남' : '여'}
          </span>
        </div>
        <p className="text-sm text-gray-500 dark:text-gray-400">#{patient.patient_number}</p>
        <div className="flex items-center space-x-3 mt-1 text-xs text-gray-400 dark:text-gray-400">
          <span>{age}세</span>
          <span>•</span>
          <span>{patient.height_cm}cm</span>
          {patient.diagnosis && (
            <>
              <span>•</span>
              <span className="truncate max-w-[100px]">{patient.diagnosis}</span>
            </>
          )}
        </div>
      </div>

      {/* 화살표 */}
      <svg className="w-5 h-5 text-gray-300 dark:text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
      </svg>
    </Link>
  );
}

function calculateAge(birthDate: string): number {
  const today = new Date();
  const birth = new Date(birthDate);
  let age = today.getFullYear() - birth.getFullYear();
  const monthDiff = today.getMonth() - birth.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
    age--;
  }
  return age;
}
