import { useState, useEffect } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { patientApi } from '../services/api';
import type { PatientCreate } from '../types';

export default function PatientForm() {
  const navigate = useNavigate();
  const { id } = useParams();
  const isEdit = Boolean(id);

  const [formData, setFormData] = useState<PatientCreate>({
    patient_number: '',
    name: '',
    gender: 'M',
    birth_date: '',
    height_cm: 0,
    diagnosis: '',
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingPatient, setLoadingPatient] = useState(isEdit);

  useEffect(() => {
    if (isEdit && id) {
      loadPatient(id);
    }
  }, [isEdit, id]);

  const loadPatient = async (patientId: string) => {
    try {
      const patient = await patientApi.getById(patientId);
      setFormData({
        patient_number: patient.patient_number,
        name: patient.name,
        gender: patient.gender,
        birth_date: patient.birth_date,
        height_cm: patient.height_cm,
        diagnosis: patient.diagnosis || '',
      });
    } catch (err) {
      setError('환자 정보를 불러오는데 실패했습니다.');
      console.error(err);
    } finally {
      setLoadingPatient(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (isEdit && id) {
        await patientApi.update(id, formData);
        navigate(`/patients/${id}`);
      } else {
        const newPatient = await patientApi.create(formData);
        navigate(`/patients/${newPatient.id}`);
      }
    } catch (err: any) {
      const message = err.response?.data?.detail || '저장에 실패했습니다. 다시 시도해주세요.';
      setError(message);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === 'height_cm' ? parseFloat(value) || 0 : value,
    }));
  };

  if (loadingPatient) {
    return (
      <div className="flex justify-center items-center py-12" role="status">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        <span className="sr-only">로딩 중...</span>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto animate-fadeIn pb-20 sm:pb-0">
      {/* 헤더 */}
      <div className="mb-6">
        <Link to="/" className="text-blue-500 text-sm font-medium flex items-center mb-2">
          <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          돌아가기
        </Link>
        <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-100">
          {isEdit ? '환자 정보 수정' : '새 환자 등록'}
        </h2>
        <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">
          {isEdit ? '환자 정보를 수정합니다.' : '새로운 환자를 등록합니다.'}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="card space-y-5">
        {error && (
          <div role="alert" className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 px-4 py-3 rounded-xl text-sm">
            {error}
          </div>
        )}

        {/* 환자번호 */}
        <div>
          <label className="label" htmlFor="patient_number">
            환자번호 <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            id="patient_number"
            name="patient_number"
            value={formData.patient_number}
            onChange={handleChange}
            required
            disabled={isEdit}
            className="input-field disabled:bg-gray-100 disabled:text-gray-500"
            placeholder="예: PT-001"
          />
        </div>

        {/* 이름 */}
        <div>
          <label className="label" htmlFor="name">
            이름 <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            id="name"
            name="name"
            value={formData.name}
            onChange={handleChange}
            required
            className="input-field"
            placeholder="환자 이름"
          />
        </div>

        {/* 성별 & 생년월일 */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label" htmlFor="gender">
              성별 <span className="text-red-500">*</span>
            </label>
            <select
              id="gender"
              name="gender"
              value={formData.gender}
              onChange={handleChange}
              required
              className="input-field"
            >
              <option value="M">남성</option>
              <option value="F">여성</option>
            </select>
          </div>
          <div>
            <label className="label" htmlFor="birth_date">
              생년월일 <span className="text-red-500">*</span>
            </label>
            <input
              type="date"
              id="birth_date"
              name="birth_date"
              value={formData.birth_date}
              onChange={handleChange}
              required
              className="input-field"
            />
          </div>
        </div>

        {/* 키 */}
        <div>
          <label className="label" htmlFor="height_cm">
            키 (cm) <span className="text-red-500">*</span>
          </label>
          <input
            type="number"
            id="height_cm"
            name="height_cm"
            value={formData.height_cm || ''}
            onChange={handleChange}
            required
            min="50"
            max="250"
            step="0.1"
            className="input-field"
            placeholder="예: 170"
          />
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            * 영상 분석 시 원근법 보정에 사용됩니다
          </p>
        </div>

        {/* 병명 */}
        <div>
          <label className="label" htmlFor="diagnosis">
            진단명 (선택)
          </label>
          <textarea
            id="diagnosis"
            name="diagnosis"
            value={formData.diagnosis}
            onChange={handleChange}
            rows={3}
            className="input-field resize-none"
            placeholder="진단명 또는 증상을 입력하세요"
          />
        </div>

        {/* 버튼 */}
        <div className="flex space-x-3 pt-4">
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="flex-1 btn-secondary"
          >
            취소
          </button>
          <button
            type="submit"
            disabled={loading}
            className="flex-1 btn-primary"
          >
            {loading ? (
              <span className="flex items-center justify-center">
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24" aria-hidden="true">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                저장 중...
              </span>
            ) : (
              isEdit ? '수정 완료' : '등록하기'
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
