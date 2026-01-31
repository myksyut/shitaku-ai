export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="text-center">
        <h1 className="text-4xl font-bold mb-4">FastAPI + NextJS Boilerplate</h1>
        <p className="text-gray-600 mb-8">
          Production-ready fullstack application template
        </p>
        <div className="flex gap-4 justify-center">
          <a
            href="/api/v1/health"
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition"
          >
            Check API Health
          </a>
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2 bg-gray-800 text-white rounded hover:bg-gray-900 transition"
          >
            API Docs (Swagger)
          </a>
        </div>
      </div>
    </main>
  )
}
