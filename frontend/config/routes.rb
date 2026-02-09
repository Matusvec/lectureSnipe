Rails.application.routes.draw do
  # Health check
  get "up" => "rails/health#show", as: :rails_health_check

  # Lecture processing routes
  root "lectures#index"
  post "lectures/process", to: "lectures#process_lecture", as: :process_lecture
  post "lectures/summary", to: "lectures#summary", as: :lecture_summary
end
